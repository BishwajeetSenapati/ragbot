cat > build.sh << 'EOF'
#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install gunicorn==21.2.0
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
EOF