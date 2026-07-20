---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'a8612053-3ae8-45db-863d-6d3af76dcc24'
  PropagateID: 'a8612053-3ae8-45db-863d-6d3af76dcc24'
  ReservedCode1: '9ced00c9-680a-4904-bfcc-cd6c6f3c97e7'
  ReservedCode2: '9ced00c9-680a-4904-bfcc-cd6c6f3c97e7'
---

# 视频平台搜索与解析参考

## 一、平台搜索URL模板

将`{keyword}`替换为搜索关键词：

| 平台 | 搜索URL | 自动搜索 | 说明 |
|------|---------|:--------:|------|
| 腾讯视频 | `https://v.qq.com/x/search/?q={keyword}` | 可用 | 搜索结果用JS点击，通过snapshot定位再点击 |
| 爱奇艺 | `https://so.iqiyi.com/so/q_{keyword}` | 可用 | 剧集链接直接在a标签href中（v_xxx.html） |
| 优酷 | `https://so.youku.com/search_video/q_{keyword}` | 不可用 | **触发滑块验证码**，需用户提供直接URL |
| 芒果TV | `https://so.mgtv.com/so?k={keyword}` | 待验证 | 可能触发验证码 |
| 哔哩哔哩 | `https://search.bilibili.com/all?keyword={keyword}` | 可用 | 搜番剧改用 `https://search.bilibili.com/bangumi?keyword={keyword}` |

## 二、平台视频链接格式

| 平台 | URL特征 | 示例 |
|------|---------|------|
| 腾讯视频 | `/x/cover/` 或 `/x/page/` | `https://v.qq.com/x/cover/m441e3rjq9kwpsc/m00253deqqo.html` |
| 爱奇艺 | `iqiyi.com/v_` 或 `iqiyi.com/a_` | `https://www.iqiyi.com/v_1pauc36ywdk.html` |
| 优酷 | `v.youku.com/v_show/id_` | `https://v.youku.com/v_show/id_XNjA0.html` |
| 芒果TV | `mgtv.com/b/` | `https://www.mgtv.com/b/336429/15694190.html` |
| 哔哩哔哩 | `/video/BV` 或 `/bangumi/play/ep` | `https://www.bilibili.com/bangumi/play/ep733245` |

## 三、平台VIP标识参考

### 爱奇艺
- 页面文本标识: `VIP`, `会员`, `付费`, `黄金会员`, `白金会员`, `星钻`, `超前点播`
- CSS类名: `.iqp-player-vip`, `.mod-vip`, `iqp-tip-vip`
- 免费内容特征: 通常标注"免费"或无VIP角标
- 超前点播: 前N集免费，后续标注"超前点播"或"用券"

### 腾讯视频
- 页面文本标识: `VIP`, `会员`, `付费`, `独播`
- CSS类名: `.txp_vip_label`, `.mod_vip_tag`, `txp-icon-vip`
- 免费内容特征: 标注"免费"或时长完整的预告
- 注意: 腾讯视频部分"独播"内容可能免费

### 优酷
- 页面文本标识: `VIP`, `会员`, `优酷VIP`, `付费`
- CSS类名: `.vip-icon`, `.control-vip`, `youku-vip`
- 免费内容特征: 通常有时长限制的试看

### 芒果TV
- 页面文本标识: `VIP`, `芒果VIP`, `会员`, `付费`
- CSS类名: `.vip-label`, `.m-vip`, `芒果VIP`

### 哔哩哔哩
- 页面文本标识: `大会员`, `付费`, `抢先看`
- CSS类名: `.vip-icon`, `.bangumi-badge-vip`
- 免费内容特征: 番剧通常首集免费，标注"大会员专享"
- 注意: B站的"大会员"标识比较明确

### VIP类型判定规则

| 检测结果 | 类型标识 | 处理建议 |
|---------|---------|---------|
| 仅标注VIP/会员 | `full` | 完全付费，解析成功率低 |
| 标注"超前点播" | `advanced` | 部分集免费可下，付费集成功率低 |
| 标注"试看" | `free_preview` | 只能下载试看片段，不推荐 |
| 有VIP角标但免费集 | `partial` | 免费集可正常下载 |
| 无任何VIP标识 | `none` | 完全免费，可正常下载 |

## 四、解析接口列表

> 更新日期: 2026-07-11 | 测试方法: Playwright m3u8拦截 + HTTP连通性检测
> ★=Playwright实测m3u8成功 | ●=HTTP PASS(含播放器特征) | ○=HTTP WEAK(仅页面可达)

### 第一梯队: Playwright实测m3u8提取成功

| 序号 | 名称 | URL前缀 | 成功率 | 状态 |
|------|------|---------|--------|------|
| 0 | 虾米解析-主线路 | `https://jx.xmflv.com/?url=` | 95% | ★ 经典稳定 |
| 1 | 虾米解析-备用 | `https://jx.xmflv.cc/?url=` | 90% | ★ 主线路备份 |
| 2 | playm3u8 | `https://www.playm3u8.cn/jiexi.php?url=` | 88% | ★ 公益无广告 |
| 3 | ckplayer | `https://www.ckplayer.vip/jiexi/?url=` | 85% | ★ |
| 4 | 盘古解析-com | `https://www.pangujiexi.com/jiexi/?url=` | 85% | ★ (.com非.cc) |
| 5 | 8090g-稳定线路 | `https://www.8090g.cn/?url=` | 85% | ★ |
| 6 | m3u8TV | `https://jx.m3u8.tv/jiexi/?url=` | 80% | ★ |

### 第二梯队: HTTP连通+播放器特征(需Playwright验证)

| 序号 | 名称 | URL前缀 | 成功率 | 状态 |
|------|------|---------|--------|------|
| 7 | yparse-ik9 | `https://yparse.ik9.cc/index.php?url=` | 78% | ● 26KB |
| 8 | yparse-com | `https://jx.yparse.com/index.php?url=` | 78% | ● 26KB |
| 9 | 剖元pouyun | `https://www.pouyun.com/?url=` | 75% | ● |
| 10 | m1907 | `https://im1907.top/?jx=` | 75% | ● |
| 11 | qianqi | `https://api.qianqi.net/vip/?url=` | 72% | ● |
| 12 | pakou-全民解析 | `https://www.pakou.cn/?url=` | 70% | ● |
| 13 | vps6-全网视频 | `https://v.vps6.cn/?url=` | 70% | ● |
| 14 | 47jx | `https://www.47jx.com/?url=` | 68% | ● |
| 15 | ejiafarm | `https://ejiafarm.com/jx.php?url=` | 65% | ● |

### 第三梯队: HTTP WEAK(页面可达但播放器特征弱)

| 序号 | 名称 | URL前缀 | 成功率 | 状态 |
|------|------|---------|--------|------|
| 16 | 618g | `https://jx.618g.com/?url=` | 55% | ○ |
| 17 | jqaaa | `https://jqaaa.com/jx.php?url=` | 55% | ○ |
| 18 | daidaitv | `https://api.daidaitv.com/index/?url=` | 50% | ○ |
| 19 | 662820 | `https://api.662820.com/xnflv/index.php?url=` | 50% | ○ |

### 已失效(不推荐使用)

| 名称 | URL前缀 | 失效原因 |
|------|---------|---------|
| 盘古解析-cc | `https://www.pangujiexi.cc/jiexi.php?url=` | 超时(.com可用) |
| okjx | `https://okjx.cc/?url=` | SSL错误 |
| 2s0 | `https://jx.2s0.cn/player/?url=` | 解析失败 |
| parwix | `https://jx.parwix.com:4433/player/?url=` | 超时 |
| apii全能VIP | `http://api.apii.top/?v=` | 超时 |
| svip.bljiex | `https://svip.bljiex.cc/?v=` | SSL错误 |

注意：解析接口不公开API，m3u8链接嵌入在混淆JS中，只能通过网络拦截获取。
接口可用性随时间变化，建议定期使用 `--health-check` 检测。

## 五、Playwright搜索策略（实测验证）

**核心原则：使用 Playwright browser_snapshot 识别搜索结果，不依赖CSS选择器。**

### 通用流程

1. `browser_navigate` 访问搜索URL
2. `browser_snapshot` 获取页面结构
3. 从snapshot中定位目标影片名称和剧集链接
4. 点击或直接导航到视频详情页
5. 从视频详情页获取可直接解析的视频URL
6. **VIP检测**：在视频详情页通过snapshot文本检测VIP标识

### 各平台实测详情

#### 腾讯视频
- 搜索结果不使用简单`<a href>`，链接通过JS click handler触发
- 需要通过snapshot找到结果项，使用`browser_click`点击进入详情
- 详情页的剧集列表也需通过snapshot定位集数并点击
- 视频URL格式：`https://v.qq.com/x/cover/{album_id}/{video_id}.html`
- VIP标识：`txp_vip_label`, "VIP", "独播"

#### 爱奇艺
- 搜索结果中的剧集链接直接可用（`<a href>` 格式）
- 剧集列表：1, 2, 3...各集有独立链接 `https://www.iqiyi.com/v_{id}.html`
- "立即播放"按钮链接到第一集
- 最容易搜索和提取链接的平台
- VIP标识：`iqp-player-vip`, "会员", "星钻", "超前点播"

#### 优酷
- **搜索触发滑块验证码，无法自动绕过**
- 用户必须提供直接的视频URL（如从手机分享链接获取）
- 反爬严格，不建议尝试自动搜索
- VIP标识：`vip-icon`, "优酷VIP"

#### 哔哩哔哩
- 综合搜索结果以UGC短视频为主
- 搜番剧应使用 `https://search.bilibili.com/bangumi?keyword={keyword}`
- 视频链接格式：`//www.bilibili.com/video/BV{xxx}/`
- 番剧链接格式：`//www.bilibili.com/bangumi/play/ep{xxx}`
- VIP标识：`.bangumi-badge-vip`, "大会员", "抢先看"

#### 芒果TV
- 未实测，按爱奇艺类似方式处理
- 如触发验证码，按优酷同等处理（要求用户提供URL）
- VIP标识：`.m-vip`, "芒果VIP"

## 六、影视命名规则

### 电视剧（常规剧集）
```
{片名}.S{季:02d}E{集:02d}.{分辨率}.{来源}.{编码}.mp4
```
示例：
- `斗罗大陆.S01E01.1080p.WEB-DL.H264.mp4`
- `庆余年.S02E15.1080p.WEB-DL.H264.mp4`

### 电影
```
{片名}.{年份}.{分辨率}.{来源}.{编码}.mp4
```
示例：
- `流浪地球2.2023.1080p.WEB-DL.H264.mp4`
- `满江红.2023.2160p.WEB-DL.H265.mp4`

### OVA（原创动画录影带）
```
{片名}.S00E{集:02d}-OVA{序号}.{分辨率}.{来源}.{编码}.mp4
```
- OVA统一使用 **S00** 作为季数标识（国际通行惯例）
- 多OVA时附带OVA序号，单OVA可省略序号
示例：
- `斗罗大陆.S00E01-OVA1.1080p.WEB-DL.H264.mp4` (多OVA)
- `庆余年.S00E01.1080p.WEB-DL.H264.mp4` (单OVA)
- `鬼灭之刃.S00E03-OVA3.1080p.WEB-DL.H264.mp4`

### SP（特别篇）
```
{片名}.SP{序号:02d}.{分辨率}.{来源}.{编码}.mp4
```
- SP使用独立编号，不占用剧集编号
示例：
- `斗罗大陆.SP01.1080p.WEB-DL.H264.mp4`
- `名侦探柯南.SP05.1080p.WEB-DL.H264.mp4`

### 番外
```
{片名}.S00E{集:02d}-番外.{分辨率}.{来源}.{编码}.mp4
```
示例：
- `三体.S00E01-番外.1080p.WEB-DL.H264.mp4`

### 内容类型判定指南

| 内容类型 | content_type参数 | 判断依据 |
|---------|-----------------|---------|
| 常规剧集 | `episode` | 正常编号的1,2,3...集，每集约40-50分钟 |
| OVA | `ova` | 标注"OVA"的特别动画，通常独立于主剧情 |
| SP特别篇 | `sp` | 标注"SP"/"特别篇"/"Special"的内容 |
| 番外 | `extra` | 标注"番外"/"外传"/"Extra"的衍生故事 |
| 电影 | `movie` | 完整电影，通常90-180分钟 |

**重要**：如果用户没有特别说明内容类型，默认按 `episode` 处理。当搜索结果页面明确标注OVA/SP/番外时，自动使用对应命名。

### 分辨率标识
| 分辨率 | 标识 |
|--------|------|
| 4K/2160p | 2160p |
| 1080p | 1080p |
| 720p | 720p |
| 480p | 480p |

### 来源标识
| 来源 | 标识 |
|------|------|
| 网络下载 | WEB-DL |
| WEB截取 | WEBRip |
| 蓝光原盘 | BluRay |
| HDTV录制 | HDTV |

### 编码标识
| 编码 | 标识 |
|------|------|
| H.264/AVC | H264 |
| H.265/HEVC | H265 |
| AV1 | AV1 |

> AI生成