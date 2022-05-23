import pytest

import mortimer.utils as utils


class TestSocialMediaPreview:
    def test_get_expected_bots(self):
        bots = utils.get_social_media_user_agents()

        assert "facebot" in bots

    def test_is_social_media_preview(self):
        ua = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
        check = utils.is_social_media_preview(ua)
        assert check
