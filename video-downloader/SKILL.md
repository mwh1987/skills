---
name: video-downloader
description: "Search and download movies/TV shows from Chinese streaming platforms (Tencent Video, iQiyi, Youku, Mango TV, Bilibili). Extract m3u8 links via browser interception and download with N_m3u8DL-CLI. Use when user mentions: '下载视频', '下载电影', '下载电视剧', '找电影', 'search movie', 'download video', '视频下载', 'm3u8', or sends a streaming platform URL and wants to download."
name_cn: 影视视频下载
description_cn: 搜索并下载腾讯视频、爱奇艺、优酷、芒果TV等平台的影视资源
create_source: super-agent-skill-creator
---

# 影视视频下载

搜索并下载国内流媒体平台的影视资源。支持腾讯视频、爱奇艺、优酷、芒果TV、哔哩哔哩等平台。

## 核心执行路径

**统一使用 Playwright MCP 工具 + PowerShell 执行下载**，脚本仅作辅助参考。

```
识别输入 → 搜索/提取链接 → VIP检测 → 确认下载(含大小预估+磁盘检查) → 清晰度选择 → 提取m3u8 → 下载(进度监控+断点续传) → 自动命名
```

---

## 一、用户交互流程（必须严格遵循）

这是整个技能的交互核心。**每个用户请求都要走这个流程**，确保下对内容、下对集数、下到正确位置。

### 步骤1: 识别用户输入类型

用户发来的消息属于以下三种之一：

| 输入类型 | 示例 | 处理方式 |
|---------|------|---------|
| **影片名称** | "帮我下载斗罗大陆" | 需要搜索 → 进入步骤2A |
| **流媒体URL** | "下载这个 https://v.qq.com/x/cover/xxx" | 跳过搜索 → 进入步骤2B |
| **模糊需求** | "我想看点电影" "最近有什么好看的下" | 不执行下载，先帮用户搜索和推荐 → 回到步骤2A |

### 步骤2A: 按名称搜索（影片名称输入）

1. **选择搜索平台**：优先爱奇艺（最易提取），其次腾讯视频、B站。优酷触发验证码，不可搜索。
2. 搜索并从snapshot中定位目标影片
3. **若搜索有多个匹配结果**（如"斗罗大陆"搜出电视剧、动画、漫画多个版本），用 question 工具让用户选择，列出：片名 / 类型 / 年份 / 集数
4. 确定目标后进入步骤2B-1

### 步骤2B: 处理流媒体URL（直接URL输入）

1. **识别平台**（匹配URL特征，见 references/platform_search.md）
2. **重要区分**：
   - 「搜索不可用」≠「URL不可用」。优酷搜索触发验证码，但用户直接给的视频URL可以正常解析下载
   - 所有平台的直接URL都能用于解析提取m3u8
3. 从URL推断片名和集数：
   - 能推断的：直接走到步骤3
   - 无法推断的：用 question 工具询问用户片名、是电影还是电视剧、集数/年份

### 步骤2B-1: VIP/付费内容检测

在进入下载确认前，**必须检测视频是否为VIP/付费内容**：

1. 在视频详情页通过 `browser_snapshot` 获取页面文本
2. 检测VIP关键词（详见五、VIP内容识别规则）
3. 根据检测结果告知用户：

| VIP类型 | 说明 | 处理方式 |
|--------|------|---------|
| **无VIP标识** | 免费内容 | 正常进入步骤3 |
| **full** (完全付费) | 仅VIP可观看 | "此内容需要会员才能观看，解析可能失败。仍要尝试吗？" |
| **advanced** (超前点播) | 前N集免费，后续需付费 | "此内容存在超前点播，部分集数可能需要会员。先尝试下载免费集？" |
| **free_preview** (试看) | 只能看前几分钟 | "此内容仅支持试看，完整版可能需要会员。仍要尝试吗？" |

用户选择继续后进入步骤3。

### 步骤3: 确认下载方案（必须执行，不可跳过）

向用户展示下载方案，**等待用户确认后才开始下载**。使用 question 工具：

**单集下载确认**：
```
即将下载：
  片名: 斗罗大陆
  类型: 电视剧
  集数: 第1集
  保存到: D:\Downloads\Videos\斗罗大陆\
  预估大小: 约400MB
  磁盘空间: D盘可用 120GB ✅
确认开始下载？
```

**电视剧批量下载确认**：
```
即将下载：
  片名: 庆余年
  类型: 电视剧
  季数: 第2季
  集数: 第1-15集（共15集）
  保存到: D:\Downloads\Videos\庆余年\
  预估总大小: 约6GB（按每集400MB估算）
  磁盘空间: D盘可用 120GB ✅
  下载模式: 流水线（边下边提取下一集链接）
确认开始下载？
```

**磁盘空间不足时**：
```
即将下载：
  片名: 庆余年
  集数: 第1-15集
  预估总大小: 约6GB
  ⚠️ 磁盘空间不足: D盘仅剩 3.2GB，需要约 6.6GB（含10%预留）
  建议: 清理磁盘或更换下载路径
确认继续？
```

**电影下载确认**：
```
即将下载：
  片名: 流浪地球2
  类型: 电影
  年份: 2023
  保存到: D:\Downloads\Videos\流浪地球2\
  预估大小: 约2GB
确认开始下载？
```

用户确认后才进入阶段2（提取m3u8）。用户可在此步骤修改任何参数。

### 步骤3-1: 清晰度选择

如果提取的m3u8是master playlist（包含多个码率变体），**需要让用户选择清晰度**：

1. 从拦截到的m3u8内容中解析 `#EXT-X-STREAM-INF` 变体列表
2. 用 question 工具让用户选择：

```
检测到多个清晰度可用：
  1. 4K (20.5Mbps) - 约2.5GB
  2. 1080P (8.2Mbps) - 约1GB  ← 推荐
  3. 720P (3.5Mbps) - 约450MB
  4. 480P (1.8Mbps) - 约230MB
请选择清晰度：
```

3. 用户选择后，使用对应变体的m3u8 URL进行下载
4. 如果只有一个变体（非master playlist），跳过此步骤

### 步骤4: 信息缺失时的追问规则

以下信息缺失时必须追问，不能用默认值代替：

| 缺失信息 | 追问方式 |
|---------|---------|
| 影片名 | "请问影片叫什么名字？" |
| 电影 vs 电视剧 | "这是电影还是电视剧？这决定了文件命名方式。" |
| 集数（电视剧） | "需要下载哪几集？可以输入如 1-10 或 1,3,5,7" |
| 季数（电视剧多季） | "这是第几季？如不指定默认为第1季" |
| 年份（电影） | "是哪一年的电影？这在文件名中会用到" |
| 内容类型 | "这是OVA/特别篇/番外吗？"（常规集数不用问） |
| 保存路径 | "保存到哪？默认 D:\Downloads\Videos\" （用户不问就不改） |

**不要主动追问的可选项**（使用默认值即可）：
- 分辨率/编码 → 下载后自动检测（master playlist时会让用户选）
- 下载工具 → 默认N_m3u8DL-CLI
- 线程数 → 默认32

### 步骤5: 下载过程中的状态反馈

| 时机 | 反馈内容 |
|------|---------|
| 开始下载单集 | "开始下载 斗罗大陆 S01E01，正在提取m3u8链接..." |
| m3u8提取成功 | "链接已获取，开始下载视频（预估约400MB）..." |
| 下载进度 | "斗罗大陆 S01E01 下载中... 45% (58/128段)" |
| 下载完成单集 | "第1集下载完成：斗罗大陆.S01E01.1080p.WEB-DL.H264.mp4 (385MB)" |
| 断点续传 | "检测到未完成的下载，继续上次进度（已有 43/128段）..." |
| 批量进度 | "已完成 3/15 集，已下载 1.2GB，正在下载第4集..." |
| 批量完成 | "全部下载完成！共15集，成功14集，失败1集（第7集），跳过0集，总计 5.3GB。失败集数可重试。" |
| 链接过期 | "第8集的m3u8链接已过期，正在重新提取..." |
| 解析失败 | "第7集m3u8提取失败，已尝试3个解析接口。跳过此集，继续下载其余集。" |
| VIP拦截 | "第12集解析失败，可能是VIP内容，跳过此集。" |

### 步骤6: 异常场景的处理策略

| 异常场景 | 处理方式 |
|---------|---------|
| 搜索无结果 | 告知用户未找到，建议换平台搜索或直接提供URL |
| 搜索到多个匹配 | 列出候选项让用户选择，不自动猜测 |
| 优酷搜索触发验证码 | 告知用户"优酷限制了自动搜索，请直接提供视频链接" |
| VIP内容 | 检测后告知用户，由用户决定是否继续尝试 |
| m3u8提取失败（所有接口） | 告知用户"解析失败，可能是VIP内容或平台限制"，建议换平台或稍后重试 |
| 单集下载失败 | 自动重试1次（重新提取m3u8），仍失败则跳过，记录到失败列表 |
| 下载中断（网络/超时） | 记录断点，下次运行时可续传；告知用户哪集失败，建议单独重下该集 |
| 磁盘空间不足 | 在下载前检查，空间不足时提前警告，建议清理磁盘或更换路径 |
| 解析站不可用 | 自动切换备用接口；若所有接口均不可用，告知用户稍后重试 |
| 已下载文件存在 | 跳过该集，避免重复下载（文件>1MB视为有效） |

---

## 二、技术工作流程

### 阶段0: 预检查

1. **解析站健康检查**（可选，首次使用或解析频繁失败时执行）：
   ```powershell
   python "C:\Users\Thinkpad\.gemini\antigravity\skills\video-downloader\scripts\m3u8_extractor.py" --health-check
   ```
   或在Playwright中直接GET各解析站首页检查可用性。

2. **磁盘空间检查**：
   ```powershell
   $drive = (Get-Item "D:\Downloads\Videos").PSDrive.Name
   $free = (Get-PSDrive -Name $drive).Free / 1GB
   Write-Host "D盘可用: $([math]::Round($free,1))GB"
   ```
   或使用脚本：
   ```powershell
   python "...\video_downloader.py" --disk-check "D:\Downloads\Videos" --need-size 6000
   ```

### 阶段1: 搜索影片

1. 若为名称（非URL），通过 Playwright browser_navigate 访问平台搜索页
2. 使用 browser_snapshot 获取页面结构，**不用CSS选择器**（各平台DOM结构变化频繁）
3. 从snapshot中定位目标影片，点击进入详情页或直接提取视频URL
4. 若为电视剧，从snapshot中获取剧集列表和集数范围
5. 若用户发来的是流媒体URL，跳过搜索
6. **VIP检测**：在视频详情页用 browser_snapshot 获取页面文本，检测VIP关键词

平台搜索URL（`{keyword}`替换为搜索词，详见 references/platform_search.md）：
- 爱奇艺: `https://so.iqiyi.com/so/q_{keyword}` ✅首选（链接直接可用）
- 腾讯视频: `https://v.qq.com/x/search/?q={keyword}` ✅可用（需snapshot点击）
- 哔哩哔哩: `https://search.bilibili.com/bangumi?keyword={keyword}` ✅可用(番剧)
- 优酷: `https://so.youku.com/search_video/q_{keyword}` ❌触发验证码，仅接受直接URL
- 芒果TV: `https://so.mgtv.com/so?k={keyword}` 待验证

### 阶段2: 提取m3u8链接

1. 构造解析URL: `https://jx.xmflv.com/?url={视频URL}`（虾米解析，成功率最高）
2. 使用 `browser_navigate` 加载解析页面
3. 使用 `browser_network_requests` 监控网络请求，拦截 `.m3u8` 请求
4. 等待15秒（`browser_wait_for time=15`）让视频加载播放
5. 若15秒后未捕获到m3u8，再等10秒（部分高码率视频需要更长时间缓冲）
6. 从网络请求中筛选m3u8链接
7. **Master Playlist检测**：
   - 如果获取到的m3u8内容包含 `#EXT-X-STREAM-INF`，说明是master playlist
   - 解析出所有变体（分辨率/码率/CODECS），让用户选择
   - 选择后使用对应变体的m3u8 URL
   - 如果只有一个m3u8链接且无 `#EXT-X-STREAM-INF`，直接使用
8. **下载大小预估**：
   - 从m3u8内容统计TS分段数和总时长
   - 根据分辨率比特率估算大小：480p~2Mbps, 720p~4Mbps, 1080p~8Mbps, 4K~20Mbps
   - 在确认下载方案时展示预估大小
9. 若第一个接口未捕获到m3u8，切换备用接口重试

备用解析接口（按成功率排序，当前共20个可用接口）：
- `https://jx.xmflv.cc/?url=` (90% ★)
- `https://www.playm3u8.cn/jiexi.php?url=` (88% ★)
- `https://www.ckplayer.vip/jiexi/?url=` (85% ★)
- `https://www.pangujiexi.com/jiexi/?url=` (85% ★)
- `https://www.8090g.cn/?url=` (85% ★)
- `https://jx.m3u8.tv/jiexi/?url=` (80% ★)
- `https://yparse.ik9.cc/index.php?url=` (78% ●)
- `https://jx.yparse.com/index.php?url=` (78% ●)
- `https://www.pouyun.com/?url=` (75% ●)
- `https://im1907.top/?jx=` (75% ●)
- `https://api.qianqi.net/vip/?url=` (72% ●)
- `https://www.pakou.cn/?url=` (70% ●)
- `https://v.vps6.cn/?url=` (70% ●)
- `https://www.47jx.com/?url=` (68% ●)
- `https://ejiafarm.com/jx.php?url=` (65% ●)
- `https://jx.618g.com/?url=` (55% ○)
- `https://jqaaa.com/jx.php?url=` (55% ○)
- `https://api.daidaitv.com/index/?url=` (50% ○)
- `https://api.662820.com/xnflv/index.php?url=` (50% ○)

> ★=Playwright实测m3u8成功 | ●=HTTP PASS | ○=HTTP WEAK
> 接口可用性随时间变化，建议定期运行健康检查。~~盘古解析.cc已超时，使用.com版~~

### 阶段3: 下载视频

1. 使用 PowerShell 调用 N_m3u8DL-CLI 下载
2. 工具路径:
   - 主力: `D:\App\N_m3u8DL-CLI_v3.0.2_with_ffmpeg_and_SimpleG\N_m3u8DL-CLI_v3.0.2.exe`
   - 备用: `D:\App\N_m3u8DL-CLI\N_m3u8DL-RE.exe`
3. 下载命令:
```powershell
& "D:\App\N_m3u8DL-CLI_v3.0.2_with_ffmpeg_and_SimpleG\N_m3u8DL-CLI_v3.0.2.exe" "<m3u8_url>" --workDir "<保存目录>" --saveName "<文件名>" --enableMuxFastStart --enableDelAfterDone --maxThreads 32
```

4. **断点续传**：
   - 下载前检查目标目录是否存在临时文件（`.m3u8dl_temp/` 目录）
   - N_m3u8DL-CLI会自动识别并继续未完成的下载
   - 如目标mp4已存在且>1MB，跳过下载
   - 如残留不可续传的临时文件，清理后重新下载

5. **进度监控**：
   - N_m3u8DL-CLI输出含分段进度 `[下载] N/M`
   - 通过 PowerShell 的 `Popen` 实时读取输出
   - 根据进度百分比向用户反馈（每10%或每30秒）

### 阶段4: 文件命名与组织

命名规则参照 [references/platform_search.md](references/platform_search.md) 中的"影视命名规则"部分。

**电视剧**: `{片名}.S{季:02d}E{集:02d}.{分辨率}.WEB-DL.{编码}.mp4`
**电影**: `{片名}.{年份}.{分辨率}.WEB-DL.{编码}.mp4`
**OVA**: `{片名}.S00E{集:02d}-OVA{序号}.{分辨率}.WEB-DL.{编码}.mp4`
**SP特别篇**: `{片名}.SP{序号:02d}.{分辨率}.WEB-DL.{编码}.mp4`
**番外**: `{片名}.S00E{集:02d}-番外.{分辨率}.WEB-DL.{编码}.mp4`

**分辨率和编码自动检测**（非硬编码），检测链：
1. 从N_m3u8DL-CLI控制台输出中提取分辨率和编码关键词
2. 若步骤1无法获取分辨率，用 ffmpeg 检测已下载文件
3. 从m3u8内容的 `CODECS` 字段提取编码信息
4. 均无法检测时默认 `1080p.WEB-DL.H264`

分辨率换算规则：
- >= 2160 → `2160p`, >= 1080 → `1080p`, >= 720 → `720p`, 其他 → `480p`

编码映射：
- `avc`/`avc1` → `H264`, `hev`/`hvc`/`hevc` → `H265`, `av01` → `AV1`

**保存目录**: `<下载根目录>/<影片名>/`
- 默认下载根目录: `D:\Downloads\Videos\`

---

## 三、m3u8链接有效期检查

m3u8链接中的vkey/token通常在2-4小时后过期。

**单集下载**：下载前用HEAD请求验证
```powershell
$response = try { Invoke-WebRequest -Uri "<m3u8_url>" -Method Head -TimeoutSec 10 -UseBasicParsing } catch { $null }
if (-not $response -or $response.StatusCode -ne 200) {
    # 链接过期，需重新提取m3u8
}
```

**批量下载**：每集下载前都必须验证m3u8是否仍可用。过期则重新提取。不可假设批量下载中链接始终有效。

---

## 四、批量下载

电视剧多集下载时：
1. 搜索影片获取剧集列表，询问用户下载范围（如"1-10集"或"全26集"）
2. **磁盘空间检查**：根据集数 × 平均每集大小估算所需空间
3. 展示下载方案（含预估大小和磁盘状态）并等待用户确认（见交互流程步骤3）
4. **流水线下载模式**（推荐，比串行快30-50%）：
   - 下载当前集的同时，在Playwright中提取下一集的m3u8
   - 因为m3u8提取需要15-25秒，而单集下载通常需要几分钟
   - 这样下一集的m3u8在下完当前集时已经准备好了
   - 实现方式：当前集开始下载后，立即用Playwright提取下一集m3u8
5. **串行模式**（备选）：
   - 逐集下载：提取m3u8 → 验证 → 下载 → 检测 → 命名 → 记录
6. **并发控制**: 最多同时下载1集（避免带宽争抢和封IP）
7. **失败重试**: 单集下载失败自动重试1次，重新提取m3u8后再试
8. **跳过已有**: 目标文件已存在且>1MB时跳过
9. 全部文件保存在同一影片名文件夹中
10. 下载完成后汇报：每集文件大小、总大小、成功/失败/跳过数

---

## 五、VIP内容识别规则

### 检测方式

在视频详情页加载后，通过 `browser_snapshot` 获取页面文本，检测以下关键词：

**通用VIP关键词**：VIP, vip, 会员, 付费, 付费观看, 独播, VIP免费, VIP用, 黄金会员, 白金会员, 超前点播, 星钻, 体育会员, 试看

**平台特定标识**：
- 爱奇艺: `.iqp-player-vip`, `.mod-vip`, `iqp-tip-vip`
- 腾讯视频: `.txp_vip_label`, `.mod_vip_tag`, `txp-icon-vip`
- 优酷: `.vip-icon`, `.control-vip`, `youku-vip`
- 芒果TV: `.vip-label`, `.m-vip`, `芒果VIP`
- 哔哩哔哩: `.vip-icon`, `.bangumi-badge-vip`, `大会员`

### VIP类型判定

| 检测到的关键词 | VIP类型 | 说明 |
|-------------|--------|------|
| 超前点播 | `advanced` | 前N集免费，后续需付费 |
| 试看 | `free_preview` | 仅能看前几分钟 |
| 其他VIP关键词 | `full` | 完全付费内容 |
| 无匹配 | None | 免费内容 |

### 注意事项
- VIP检测只是**提示性质**，不阻止用户尝试下载
- 部分VIP内容可能通过解析站绕过（不保证成功率）
- 检测结果用于告知用户风险，避免浪费时间

---

## 六、解析站可用性监测

### 何时检查

- 首次使用本技能时
- m3u8提取频繁失败时
- 用户主动要求时

### 检查方式

```powershell
# 方式1: 使用脚本
python "C:\Users\Thinkpad\.gemini\antigravity\skills\video-downloader\scripts\m3u8_extractor.py" --health-check

# 方式2: PowerShell直接检查
$apis = @(
    "https://jx.xmflv.com/",
    "https://jx.xmflv.cc/",
    "https://www.playm3u8.cn/jiexi.php",
    "https://www.ckplayer.vip/jiexi/",
    "https://www.pangujiexi.com/jiexi/",
    "https://www.8090g.cn/",
    "https://jx.m3u8.tv/jiexi/",
    "https://yparse.ik9.cc/index.php",
    "https://jx.yparse.com/index.php",
    "https://www.pouyun.com/",
    "https://im1907.top/",
    "https://api.qianqi.net/vip/",
    "https://www.pakou.cn/",
    "https://v.vps6.cn/",
    "https://www.47jx.com/",
    "https://ejiafarm.com/jx.php"
)
foreach ($api in $apis) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $r = Invoke-WebRequest -Uri $api -TimeoutSec 10 -UseBasicParsing
        $sw.Stop()
        Write-Host "OK  $($sw.ElapsedMilliseconds)ms  $api"
    } catch {
        $sw.Stop()
        Write-Host "ERR $($sw.ElapsedMilliseconds)ms  $api  $($_.Exception.Message)"
    }
}
```

### 结果判定

| 状态 | 条件 | 处理 |
|------|------|------|
| healthy | 200 + <5秒 | 正常使用 |
| degraded | 200 + >5秒 | 可用但慢，超时风险大 |
| down | 非200/超时/域名停用 | 跳过此接口 |

---

## 七、脚本资源（辅助参考）

脚本为独立可执行版本，供需要时使用，不作为主要执行路径：
- `scripts/m3u8_extractor.py` - m3u8链接提取、master playlist解析、大小预估、VIP检测、解析站监测
- `scripts/video_downloader.py` - N_m3u8DL下载封装（含命名、ffmpeg检测、批量逻辑、重试、磁盘检查、进度监控、断点续传、OVA/SP命名）

注意：独立运行脚本需额外安装 Playwright Chromium（`python -m playwright install chromium`），主执行路径（Playwright MCP）无此要求。
