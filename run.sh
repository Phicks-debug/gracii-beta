#!/bin/bash
npm run dev -- --host 0.0.0.0 &
uvicorn main:app --host 0.0.0.0 --port 8000 --reload