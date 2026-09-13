#!/usr/bin/env bash
echo "======================================================="
echo "  Launching TalentOps AI OS Mini..."
echo "======================================================="
echo ""
python -m uvicorn web.app:app --host 127.0.0.1 --port 8080 --reload
