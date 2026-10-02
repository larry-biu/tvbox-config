# Larry 家庭影视配置

这是 `larry-biu` 自己维护的影视仓／TVBox／FongMi 配置。参考用户提供的 [影仓吧 Link3](https://link3.cc/uuccc) 和 `mao.txt`，重新整理中文影视、网盘、少儿教育和直播入口。配置、JAR、分类文件和直播发布文件均在本仓库；不需要 Mac 运行服务。

## 直接导入

**影视仓「配置地址」优先填写：**

```text
https://larry-biu.github.io/tvbox-config/config-pages.json
```

GitHub Raw 同版本入口：

```text
https://raw.githubusercontent.com/larry-biu/tvbox-config/main/config.json
```

| 软件／用途 | GitHub Pages 地址 |
| --- | --- |
| 影视仓新版、常见TVBox新版 | `https://larry-biu.github.io/tvbox-config/config-pages.json` |
| TVBox旧版直播格式 | `https://larry-biu.github.io/tvbox-config/tvbox-pages.json` |
| FongMi／OK影视 | `https://larry-biu.github.io/tvbox-config/fongmi-pages.json` |
| 支持多仓的影视仓 | `https://larry-biu.github.io/tvbox-config/warehouse-pages.json` |
| 只替换原应用的直播地址 | `https://larry-biu.github.io/tvbox-config/live/live.txt` |
| IPTV播放器、VLC播放列表 | `https://larry-biu.github.io/tvbox-config/live/live.m3u` |

GitHub Raw 的适配文件分别为根目录 `config.json`、`tvbox.json`、`fongmi.json`、`warehouse.json`；Raw直播为 `https://raw.githubusercontent.com/larry-biu/tvbox-config/main/live/live.txt`。Pages文件的全部自管依赖走Pages，Raw文件的全部自管依赖走Raw，不混用第三方GitHub代理。

导入前在应用内备份旧配置，填地址、保存并加载。首页默认量子影视；使用搜索查电影、电视剧、动漫，或切换非凡、如意、网盘和少儿入口。网盘需要用户自己的授权，没有内置共享账号。资源名中的4K等是来源声明，不替用户删掉低画质档位，也不证明实际分辨率。

## 本次内容与验证

18个点播／辅助入口：量子影视、非凡影视、如意影视、玩偶哥哥、木偶、多多、戏曲、相声小品、演唱会、音乐MV、哔哩哔哩、影视解说、少儿教育、小学课堂、初中课堂、高中教育、本地视频、网盘与播放器设置。

直播条目数、分组与缺项以 [live/status.json](live/status.json) 为准。央视、各省卫视为主，粤语港澳台和英语随权威输出补充；当前缺项不以配置成功代替覆盖完成。同节目不同画质及线路按输入原样保留。

- 三个资源API已匿名核验分类、搜索和详情，详情含剧集地址。尚未播放这些媒体。
- 两份JAR为真实ZIP，已检查所需DEX类并锁定MD5／SHA256；十份分类JSON已下载并清空共享Cookie，均托管在本仓库。没有在Mac执行第三方JAR。
- 所有自管资源、JSON结构、JAR MD5、发布SHA256、旧镜像／Mac地址／共享凭证残留均由检查脚本校验；GitHub每次push运行同样检查。
- 仍需用户电视验收：配置导入、搜索、起播、网盘授权、音画、换台、重启和各画质兼容；西安联通及长期稳定性尚未证明。

原参考中的成人站入口、旧GitHub代理、共享Cookie／appkey及第三方VIP解析未采用。分类过滤用于首页组织，不承诺过滤所有站点搜索结果。设备原订阅没有被远程改动。

## 自动维护与回退

已改为GitHub自动运行，无需用户手工更新：

- 约每6小时读取主入口与备用入口，跟随选定站点的接口、网盘域名、JAR与分类变化。
- 只同步本配置选定入口，不自动扩大频道或引入共享账号。清除共享Cookie，检查JAR ZIP/DEX类和声明MD5，再核验资源API分类、搜索与详情。
- 可读取的资源API优先显示。候选失败时保留上一版配置，下次任务自动重试；作者停更或所有源失效时不会伪造成功。
- 每次运行提交健康记录，自动发布Pages，并匿名回读实际文件和资源哈希。任务采用并发锁，不强推删除历史。
- 直播在GitHub云端检测现有清单的HTTP可达性，外网或地区限制不会自动删节目。目前不自动采集替换直播地址；直播失效记录在健康状态中。点播更新和直播检查都不依赖Mac开机。
- GitHub另有每6小时运行的云端巡检：维护任务失败或超过12小时未运行时重新触发；维护任务被停用时尝试重新启用。没有本机定时任务。

[健康状态](health.json)记录最近尝试、最近成功、来源、接口验证和直播抽样；不是设备实播凭证。GitHub调度可能排队，维护频率不是精确时间保证。使用者的播放器刷新配置后取得新版；是否自动刷新取决于客户端。

GitHub提交历史保留回退依据，资源按内容哈希命名。文件下载成功、配置校验通过和电视起播分别记录。外部作者、资源站和用户自己的网盘授权仍可能变化；自动更新解决维护流程，不能保证第三方永久服务。

[参考核查](source/reference-review.json) · [点播API核查](source/vod-verification.json) · [自动任务](https://github.com/larry-biu/tvbox-config/actions/workflows/maintain.yml)
