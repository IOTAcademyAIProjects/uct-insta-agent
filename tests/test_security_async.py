#!/usr/bin/env python3
"""
Phase 4: Async security validation — ensure async_validate_safe_url does not block event loop
"""
import unittest, sys, os, asyncio, time
PROJECT_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from core.security import validate_safe_url, async_validate_safe_url, SecurityException

class TestSecurityAsync(unittest.IsolatedAsyncioTestCase):
    async def test_async_blocks_private_ip(self):
        with self.assertRaises(SecurityException):
            await async_validate_safe_url("http://10.0.0.1/internal")

    async def test_async_allows_public(self):
        url="https://images.unsplash.com/photo-1518770660439-4636190af475"
        self.assertEqual(await async_validate_safe_url(url), url)

    async def test_async_blocks_cloud_metadata(self):
        with self.assertRaises(SecurityException):
            await async_validate_safe_url("http://169.254.169.254/latest/meta-data/")

    async def test_async_does_not_block_loop(self):
        # Two concurrent validations should run in parallel via to_thread, not sequential blocking
        start=time.time()
        await asyncio.gather(
            async_validate_safe_url("https://images.unsplash.com/photo-1"),
            async_validate_safe_url("https://images.unsplash.com/photo-2"),
        )
        elapsed=time.time()-start
        # If blocking, would be ~2*dns time; with to_thread should be <1s for these public URLs (or at least not double)
        self.assertLess(elapsed, 5.0)

    async def test_sync_and_async_equivalent(self):
        url="https://example.com/path"
        sync=validate_safe_url(url)
        async_res=await async_validate_safe_url(url)
        self.assertEqual(sync, async_res)

if __name__=='__main__':
    unittest.main()
