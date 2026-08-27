#!/usr/bin/env python3
"""
Integration tests for FastAPI health + self-improve endpoints
"""
import unittest, sys, os
PROJECT_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ["ALLOW_OPEN"]="true"
from fastapi.testclient import TestClient
import api
from db.setup_db import setup_database

class TestAPI(unittest.TestCase):
    def setUp(self):
        setup_database()
        self.client=TestClient(api.app)

    def test_health(self):
        r=self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"],"ok")

    def test_models_status(self):
        r=self.client.get("/api/v3/models/status")
        self.assertEqual(r.status_code, 200)
        self.assertIn("providers", r.json())

    def test_self_improve_flow(self):
        # propose
        r=self.client.post("/api/v3/self-improve/propose?brand_id=1&dry_run=true")
        self.assertEqual(r.status_code, 200)
        j=r.json()
        # May be blocked if already exists for week, but should return proposed or reason
        self.assertTrue("proposed" in j or "existing" in str(j))
        # pending
        r2=self.client.get("/api/v3/self-improve/pending?brand_id=1")
        self.assertEqual(r2.status_code,200)
        self.assertIn("pending", r2.json())
        # history
        r3=self.client.get("/api/v3/self-improve/history?brand_id=1")
        self.assertEqual(r3.status_code,200)
        self.assertIn("history", r3.json())

    def test_brands(self):
        r=self.client.get("/api/v3/brands")
        self.assertEqual(r.status_code,200)
        self.assertIn("brands", r.json())

    def test_intelligence(self):
        r=self.client.get("/api/v3/intelligence/trends?brand_id=1")
        self.assertEqual(r.status_code,200)
        r2=self.client.get("/api/v3/intelligence/brief?brand_id=1")
        self.assertEqual(r2.status_code,200)

if __name__=='__main__':
    unittest.main()
