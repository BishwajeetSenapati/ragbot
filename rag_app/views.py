import json
import os
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Document, ChatSession, Message, Source
from .rag_pipeline import delete_document_chunks, index_document, answer_question, summarize_document
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password


@login_required(login_url='/login/')
def index(request):
    return render(request, "rag_app/index.html")


@login_required(login_url='/login/')
def chat(request):
    return render(request, "rag_app/chat.html")


@login_required(login_url='/login/')
def documents(request):
    return render(request, "rag_app/documents.html")


# ── Documents ─────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
@csrf_exempt
@require_http_methods(["POST"])
def upload_document(request):
    import tempfile
    import threading

    files = request.FILES.getlist("documents")
    if not files:
        return JsonResponse({"error": "No files provided"}, status=400)

    allowed = {".pdf", ".txt", ".docx"}
    saved   = []

    for f in files:
        ext = "." + f.name.split(".")[-1].lower()
        if ext not in allowed:
            return JsonResponse({"error": f"Unsupported file: {f.name}"}, status=400)

        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in f.chunks():
            tmp.write(chunk)
        tmp.close()
        temp_path = tmp.name

        doc = Document.objects.create(
            user=request.user,
            name=f.name,
            file_type=ext.replace(".", ""),
            size=f.size,
            status="processing",
        )
        saved.append((doc, temp_path))

    # Index in background so request returns immediately
    def index_in_background(doc_id, temp_path, user_id):
        from .rag_pipeline import index_document, summarize_document
        from .models import Document as Doc
        import os

        try:
            doc = Doc.objects.get(id=doc_id)

            # Summary first
            try:
                doc.summary = summarize_document(temp_path)
                print(f"Summary generated ✅")
            except Exception as e:
                print(f"SUMMARY ERROR: {e}")
                doc.summary = ""

            # Then index
            chunk_count = index_document(temp_path, user_id, doc_id)
            doc.chunk_count = chunk_count
            doc.status = "ready"
            print(f"Indexing complete ✅")

        except Exception as e:
            print(f"INDEXING ERROR: {e}")
            import traceback
            traceback.print_exc()
            try:
                doc = Doc.objects.get(id=doc_id)
                doc.status = "failed"
                doc.save()
            except Exception:
                pass

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                print(f"Temp file deleted ✅")

        try:
            doc.save()
        except Exception:
            pass

    for doc, temp_path in saved:
        thread = threading.Thread(
            target=index_in_background,
            args=(doc.id, temp_path, request.user.id)
        )
        thread.daemon = True
        thread.start()
        print(f"Background indexing started: {doc.name}")

    return JsonResponse({
        "success": True,
        "message": f"{len(saved)} file(s) uploaded! Indexing in background — please wait 2-3 minutes then refresh.",
        "documents": [
            {"id": d.id, "name": d.name, "status": d.status}
            for d, _ in saved
        ],
    })


@login_required(login_url='/login/')
@require_http_methods(["GET"])
def list_documents(request):
    docs = Document.objects.filter(user=request.user).order_by("-uploaded_at")
    return JsonResponse({
        "documents": [
            {
                "id":          d.id,
                "name":        d.name,
                "file_type":   d.file_type,
                "size":        d.size,
                "chunk_count": d.chunk_count,
                "summary":     d.summary,
                "status":      d.status,
                "uploaded_at": d.uploaded_at.strftime("%Y-%m-%d %H:%M"),
            }
            for d in docs
        ]
    })


@login_required(login_url='/login/')
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_document(request, doc_id):
    try:
        doc = Document.objects.get(id=doc_id, user=request.user)

        # Delete from Pinecone
        try:
            delete_document_chunks(request.user.id, doc.id)
        except Exception as e:
            print(f"Warning: failed to delete from Pinecone: {e}")

        doc.delete()
        return JsonResponse({"success": True, "message": "Document deleted."})
    except Document.DoesNotExist:
        return JsonResponse({"error": "Document not found."}, status=404)


# ── Chat Sessions ─────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
    session = ChatSession.objects.create(user=request.user, title="New Chat")
    return JsonResponse({
        "session_id": str(session.session_id),
        "title":      session.title,
        "created_at": session.created_at.strftime("%Y-%m-%d %H:%M"),
    })


@login_required(login_url='/login/')
@require_http_methods(["GET"])
def list_sessions(request):
    sessions = ChatSession.objects.filter(user=request.user).order_by("-last_active")
    return JsonResponse({
        "sessions": [
            {
                "session_id":  str(s.session_id),
                "title":       s.title,
                "last_active": s.last_active.strftime("%Y-%m-%d %H:%M"),
            }
            for s in sessions
        ]
    })


# ── Messages ──────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
@require_http_methods(["GET"])
def get_messages(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

    messages = session.messages.all().order_by("created_at")
    return JsonResponse({
        "session_id": str(session.session_id),
        "title":      session.title,
        "messages": [
            {
                "id":         m.id,
                "role":       m.role,
                "content":    m.content,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M"),
                "sources": [
                    {
                        "document": s.document.name if s.document else "Unknown",
                        "page":     s.page_number,
                        "snippet":  s.snippet,
                    }
                    for s in m.sources.all()
                ] if m.role == "assistant" else [],
            }
            for m in messages
        ],
    })


# ── Ask Question ──────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
@csrf_exempt
@require_http_methods(["POST"])
def ask_question(request):
    try:
        body       = json.loads(request.body)
        question   = body.get("question", "").strip()
        session_id = body.get("session_id")
    except Exception:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    if not question:
        return JsonResponse({"error": "Question is required."}, status=400)

    if not session_id:
        return JsonResponse({"error": "Session ID is required."}, status=400)

    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

    Message.objects.create(
        session=session,
        role="user",
        content=question,
    )

    doc_ids = body.get("doc_ids", [])

    try:
        result       = answer_question(question, request.user.id, doc_ids=doc_ids)
        answer       = result["answer"]
        sources_data = result["sources"]
    except Exception as e:
        answer       = f"Error: {str(e)}"
        sources_data = []

    assistant_msg = Message.objects.create(
        session=session,
        role="assistant",
        content=answer,
    )

    for src in sources_data:
        Source.objects.create(
            message=assistant_msg,
            page_number=src.get("page", 0),
            snippet=src.get("snippet", ""),
        )

    if session.title == "New Chat":
        session.title = question[:50]
        session.save()

    return JsonResponse({
        "answer":     answer,
        "sources":    sources_data,
        "session_id": str(session.session_id),
    })


# ── Authentication Views ──────────────────────────────────────────────────────

def signup_page(request):
    return render(request, "rag_app/signup.html")


def login_page(request):
    return render(request, "rag_app/login.html")


@csrf_exempt
@require_http_methods(["POST"])
def signup_user(request):
    try:
        body     = json.loads(request.body)
        username = body.get("username", "").strip()
        email    = body.get("email", "").strip()
        password = body.get("password", "").strip()
    except Exception:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    if not username or not password:
        return JsonResponse({"error": "Username and password are required."}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already taken."}, status=400)

    if len(password) < 6:
        return JsonResponse({"error": "Password must be at least 6 characters."}, status=400)

    user = User.objects.create(
        username=username,
        email=email,
        password=make_password(password),
    )

    login(request, user)
    return JsonResponse({"success": True, "message": "Account created successfully."})


@csrf_exempt
@require_http_methods(["POST"])
def login_user(request):
    try:
        body     = json.loads(request.body)
        username = body.get("username", "").strip()
        password = body.get("password", "").strip()
    except Exception:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse({"error": "Invalid username or password."}, status=400)

    login(request, user)
    return JsonResponse({"success": True, "message": "Logged in successfully."})


@require_http_methods(["GET", "POST"])
def logout_user(request):
    logout(request)
    from django.shortcuts import redirect
    return redirect("login_page")


# ── Clear / Delete Sessions ───────────────────────────────────────────────────

@login_required(login_url='/login/')
@csrf_exempt
@require_http_methods(["DELETE"])
def clear_session_messages(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

    session.messages.all().delete()
    session.title = "New Chat"
    session.save()
    return JsonResponse({"success": True, "message": "Chat history cleared."})


@login_required(login_url='/login/')
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

    session.delete()
    return JsonResponse({"success": True, "message": "Session deleted."})
