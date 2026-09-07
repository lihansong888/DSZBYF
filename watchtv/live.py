import requests
import re
import os

# ========== 填写源的地址 ==========
URL_LIST = [
    "https://raw.githubusercontent.com/fafa002/yf2025/refs/heads/main/yiyifafa.txt"
]

# ========== 分组映射：左边是源里的分组名，右边是输出时改后的分组名（yifa） ==========
GROUP_MAP = {
    "咪咕央视": "hansong咪咕央卫直播2",
    "今日影视": "hansong港澳台2",
}

# ========== 要屏蔽的节目：频道名【包含】以下任意关键词的，会被剔除不输出 ==========
# 例：想屏蔽"测试"频道 → 填 "测试"；想屏蔽"风云"频道 → 填 "风云"
# 想精确屏蔽某个频道，就把完整频道名填上
# 留空 [] 表示不屏蔽任何节目
EXCLUDE_KEYWORDS = [
     "需切换EXO解码",
    "请勿打赏",
]

def parse_any(text: str):
    res = []
    extinf_line = None
    current_group = None
    for raw_line in text.splitlines():
        ln = raw_line.strip()
        if not ln:
            continue
        if ln.startswith("#EXTINF:"):
            extinf_line = ln
            continue
        if extinf_line is not None and not ln.startswith("#"):
            res.append((extinf_line, ln))
            extinf_line = None
            continue
        if ',' in ln and not ln.startswith("#"):
            sp = ln.split(',',1)
            name_part = sp[0].strip()
            url_part = sp[1].strip()
            if url_part == "#genre#":
                current_group = name_part
                continue
            if current_group:
                fake_ext = f'#EXTINF:-1 group-title="{current_group}",{name_part}'
            else:
                fake_ext = f'#EXTINF:-1,{name_part}'
            res.append((fake_ext, url_part))
    return res

def get_channel_name(extinf):
    if "," in extinf:
        return extinf.split(",")[-1].strip()
    return ""

def get_group_title(extinf):
    m = re.search(r'group-title="([^"]+)"', extinf)
    if m:
        return m.group(1).strip()
    return ""

def main():
    # 用改后的分组名初始化空列表
    group_bucket = {v: [] for v in GROUP_MAP.values()}
    seen = set()
    blocked_cnt = 0
    for url in URL_LIST:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            channels = parse_any(resp.text)
            for extinf, play_url in channels:
                ch_name = get_channel_name(extinf)
                ch_group = get_group_title(extinf)
                # 只保留 GROUP_MAP 里有的分组，其他全屏蔽
                if ch_group not in GROUP_MAP:
                    continue
                # ===== 屏蔽指定节目 =====
                if any(k in ch_name for k in EXCLUDE_KEYWORDS):
                    blocked_cnt += 1
                    continue
                # 关键：查映射表，把源分组名改成输出分组名
                output_group = GROUP_MAP[ch_group]
                item_key = (ch_name, play_url)
                if item_key not in seen:
                    seen.add(item_key)
                    group_bucket[output_group].append((ch_name, play_url))
        except Exception as e:
            print(f"⚠️ 拉取 {url} 失败：{e}")
    total_cnt = sum(len(v) for v in group_bucket.values())
    print(f"✅筛选结束，共提取 {total_cnt} 个频道（已屏蔽 {blocked_cnt} 个）")
    for gname, ch_list in group_bucket.items():
        print(f"  - {gname}: {len(ch_list)} 个频道")
    out_dir = os.path.dirname(os.path.abspath(__file__))
    output_m3u = ["#EXTM3U"]
    for gname, ch_list in group_bucket.items():
        for cname, curl in ch_list:
            # 输出时用改后的分组名
            fake_ext = f'#EXTINF:-1 group-title="{gname}",{cname}'
            output_m3u.append(fake_ext)
            output_m3u.append(curl)
    m3u8_path = os.path.join(out_dir, "live.m3u8")
    with open(m3u8_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_m3u))
    print(f"✅已输出 m3u8：{m3u8_path}")

if __name__ == "__main__":
    main()
