#!/usr/bin/env python3
"""
Contract tests for PlatformAdapter and PublisherAgent
"""
import unittest, sys, os
PROJECT_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from adapters.base import PlatformAdapter, MediaSpec
from adapters.instagram import InstagramAdapter
from adapters.linkedin import LinkedInAdapter
from adapters.twitter import TwitterAdapter
from adapters.youtube import YouTubeAdapter
from agents.publisher_agent import PublisherAgent

class TestPlatformContracts(unittest.TestCase):
    def test_media_spec_limits(self):
        for Adapter in [InstagramAdapter, LinkedInAdapter, TwitterAdapter, YouTubeAdapter]:
            ad=Adapter()
            for ptype in ["FEED","STORY","REEL","CAROUSEL"]:
                spec=ad.get_media_spec(post_type=ptype)
                self.assertIsInstance(spec, MediaSpec)
                # STORY may have 0 caption length (no caption)
                if ptype == "STORY":
                    self.assertGreaterEqual(spec.max_caption_length, 0)
                else:
                    self.assertGreater(spec.max_caption_length, 0)
                self.assertGreater(len(spec.aspect_ratios), 0)

    def test_format_caption_truncates(self):
        ad=InstagramAdapter()
        long="a"*5000
        fmt=ad.format_caption(long)
        self.assertLessEqual(len(fmt), 2200)
        # LinkedIn 3000
        li=LinkedInAdapter()
        self.assertLessEqual(len(li.format_caption(long)), 3000)
        # Twitter 280
        tw=TwitterAdapter()
        self.assertLessEqual(len(tw.format_caption(long)), 280)

    def test_publish_without_keys_returns_error_not_crash(self):
        # Ensure no COMPOSIO key -> PublishResult success False not exception
        old=os.getenv("COMPOSIO_API_KEY")
        if old:
            os.environ.pop("COMPOSIO_API_KEY", None)
        try:
            pub=PublisherAgent()
            res=pub.publish(media_urls=["https://example.com/img.jpg"], caption="test", platforms=["INSTAGRAM"])
            self.assertIn("INSTAGRAM", res)
            self.assertFalse(res["INSTAGRAM"].success)
            self.assertIn("COMPOSIO_API_KEY", res["INSTAGRAM"].error)
        finally:
            if old:
                os.environ["COMPOSIO_API_KEY"]=old

    def test_publisher_unknown_platform(self):
        pub=PublisherAgent()
        res=pub.publish(media_urls=["https://example.com/a.jpg"], caption="hi", platforms=["UNKNOWN"])
        self.assertIn("UNKNOWN", res)
        self.assertFalse(res["UNKNOWN"].success)

    def test_instagram_response_validation(self):
        ig=InstagramAdapter()
        ok,cid,err=ig._validate_action_response({"data":{"id":"123"}}, "TEST")
        self.assertTrue(ok)
        ok,cid,err=ig._validate_action_response({"successful":False,"error":"bad"}, "TEST")
        self.assertFalse(ok)

if __name__=='__main__':
    unittest.main()
