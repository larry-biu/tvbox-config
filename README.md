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

## 维护与回退

权威配置选择是 [source/selection.json](source/selection.json)。辅助资源来源见 [source/asset-sources.json](source/asset-sources.json)，哈希锁定见 [source/asset-manifest.json](source/asset-manifest.json)。只修改权威选择后重新生成，避免手改八个播放器入口造成不一致。

```sh
python3 scripts/build.py
python3 scripts/build.py --check
```

需要更新第三方JAR／分类时显式运行以下命令。更新工具不会执行JAR，会检查ZIP与必需类、清空共享凭证；全部资源读取成功才切换资源清单。审查差异并完成必要的设备验证后，再提交和推送。资源按内容哈希命名，旧文件保留，因此回退旧配置仍有对应JAR和分类。

```sh
python3 scripts/refresh_assets.py
python3 scripts/build.py
python3 scripts/build.py --check
```

直播由项目的独立维护流程负责，本仓库只接收其 `live-list/output/` 产物。发布快照不会脱离该权威入口再建一套采集规则。源更新后，本机 `app-config/publish.py` 重新生成并提交推送；GitHub不会自动知道尚未发布的本机变化。暂未安装定时任务，避免把未知状态自动覆盖成默认。

GitHub提交记录是回退点。要恢复之前的已验收版本，使用 `git revert` 生成恢复提交并推送，不强推删除历史。固定URL继续有效；如需锁死某次版本，可把Raw地址里的 `main` 替换成那次提交SHA。完整出版哈希在 [manifest.json](manifest.json)。

[参考核查](source/reference-review.json) · [点播API核查](source/vod-verification.json)
