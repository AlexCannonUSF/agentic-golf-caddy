# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from utils.profile_manager import ProfileManager


EXPECTED_BENCHMARK_STEMS = {
    "benchmark_shotscope_0hcp_male",
    "benchmark_shotscope_5hcp_male",
    "benchmark_shotscope_10hcp_male",
    "benchmark_shotscope_15hcp_male",
    "benchmark_shotscope_20hcp_male",
    "benchmark_shotscope_25hcp_male",
    "benchmark_trackman_pga_tour_2024",
    "benchmark_trackman_lpga_tour_2024",
}


def test_benchmark_profiles_load_from_repo() -> None:
    manager = ProfileManager()
    available = set(manager.list_profiles())

    assert EXPECTED_BENCHMARK_STEMS.issubset(available)

    for stem in sorted(EXPECTED_BENCHMARK_STEMS):
        profile = manager.load_profile(stem)
        assert len(profile.club_distances) >= 8
        assert profile.name
