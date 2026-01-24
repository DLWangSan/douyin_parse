from douyin_video_parser import DouyinVideoParser, get_nwm_url


# Demo: Single video download
def demo_single_video():
    video_url = "https://v.douyin.com/pEkgDrA5nsk"
    parser = DouyinVideoParser()
    info = parser.parse_video(video_url)
    print(info)


def demo_user_home_list():
    user_home = (
        "https://www.douyin.com/user/MS4wLjABAAAAc8zBUlm6BFIMdkOHRhRwvtzswRAuJ8D1pcWjsALGjS4tZhumG95Yxt7WVm--EUnJ"
        "?from_tab_name=main"
    )
    parser = DouyinVideoParser()
    urls = parser.get_user_aweme_urls(user_home, max_pages=3)
    print("total:", len(urls))
    for u in urls:
        print(u)


def demo_from_video_to_user_list():
    video_url = "https://v.douyin.com/pEkgDrA5nsk"
    parser = DouyinVideoParser()
    urls = parser.get_user_aweme_urls_from_video_url(video_url, max_pages=3)
    print("total:", len(urls))
    for u in urls:
        print(u)


if __name__ == "__main__":
    demo_single_video()
    # demo_user_home_list()
    # demo_from_video_to_user_list()

