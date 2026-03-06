def post_to_wp(article,site_key):
    cfg=WP_SITES[site_key]
    if not cfg["password"]: return None
    src=article["source"]; lnk=article["link"]
    c=f"<p><em>Fonte: <a href={lnk!r}>{src}</a></em></p><p>{article["summary"]}...</p>"
    try:
        r=requests.post(f"{cfg["url"]}/wp-json/wp/v2/posts",
            json={"title":article["title"],"content":c,"status":"draft"},
            auth=(cfg["user"],cfg["password"]),timeout=30)
        r.raise_for_status(); print(f"  POSTED: {article["title"][:50]}"); return r.json()["id"]
    except Exception as e: print(f"  FAIL:{e}"); return None

def run(site="all",max_posts=5,dry_run=False):
    print(f"RSS Aggregator | {datetime.now():%Y-%m-%d %H:%M}")
    cache=load_cache()
    sites=list(WP_SITES.keys()) if site=="all" else [site]
    total=0
    for sk in sites:
        print(f"
{sk.upper()}:")
        scored=sorted([(score_article(a,sk),a) for a in fetch_feeds(sk)],key=lambda x:x[0],reverse=True)
        n=0
        for score,a in scored:
            if n>=max_posts or score<40: continue
            uid=hash_url(a["link"])
            if uid in cache: continue
            print(f"  [{score}] {a["title"][:65]}")
            if not dry_run:
                pid=post_to_wp(a,sk)
                if pid:
                    cache[uid]={"posted":datetime.now().isoformat(),"site":sk}
                    save_cache(cache); n+=1; total+=1; time.sleep(2)
            else: n+=1; total+=1
    print(f"
Done: {total}")

if __name__=="__main__":
    import argparse; p=argparse.ArgumentParser()
    p.add_argument("--site",default="all",choices=["all","ai","basket","crypto"])
    p.add_argument("--max",type=int,default=5)
    p.add_argument("--dry-run",action="store_true")
    a=p.parse_args(); run(a.site,a.max,a.dry_run)
