# MaiBot自动重启插件

一个提供阈值触发重启和定时重启功能的插件。可以缓解MaiBot长时间运行下占用上升的问题。

## 功能

- 监测CPU占用，超过设定阈值则重启MaiBot

- 监测内存占用，超过设定阈值则重启MaiBot

- 定时重启，到达设定时间时自动重启MaiBot

- 手动重启，发送 **/restart** 手动重启MaiBot

- 权限校验，通过 **admin_ids** 管理员用户 ID 列表限制 /restart 与重启动作的可用成员（默认为空，不校验）

## 安装

### 方式一

在MaiBot插件市场中搜索并安装本插件。

### 方式二

手动克隆本插件至插件目录。

```bash
cd /root/MaiBot/plugins
git clone https://github.com/lnrh1/maibot-auto-restart.git
```

## 配置

```toml
enable_threshold_monitor = true
```

**是否启用阈值监测**，为false则禁用阈值监测，为true则启用阈值监测。默认为true.

```toml
memory_threshold_percent = 80
```

**内存阈值百分比**，若监测到的内存占用超过设定值，则触发重启。默认为80.

```toml
cpu_threshold_percent = 90
```

**CPU阈值百分比**，若监测到的CPU占用超过设定值，则触发重启。默认为90.



```toml
enable_schedule_restart = false
```

**是否启用定时重启**，为false则禁用定时重启，为true则启用定时重启。默认为false.

```toml
restart_time = "04:00"
```

**定时重启时间**，采用24小时制，格式为 HH:MM 。到达该时间则触发重启。默认为"04:00".



```toml
admin_ids = []
```

**管理员用户 ID 列表**，用于校验 **/restart** 命令及 trigger_restart 的发起者身份。为空则不校验。默认为空。



```toml
restart_delay_seconds = 5
```

**重启前延迟秒数**，触发重启前将等待该时长后再执行重启。默认为5.

```toml
notify_before_manual_restart = true
```

**手动重启前是否发送通知**，为false则手动重启时不发送通知，为true则手动重启时发送通知。默认为true.

```toml
webui_port = 8001
```

**WebUI端口**，用于发送重启请求。默认为8001.

```toml
access_token = ""
```

**Access Token**，用于构造重启请求，必填。

## 命令

```context
/restart
```

手动触发重启。（仅管理员可用）

```context
/restart_status
```

查看插件状态。

## 动作

```context
trigger_restart
```

作为工具交给Agent调用进行手动重启。（仅管理员私聊中可用）

## 重启原理

触发重启时，插件将利用Access Token构造重启请求，发送至本地WebUI，由MaiBot完成重启。

```mermaid
flowchart LR
    A[构造请求] --> B[发送至本地WebUI]
    B --> C[MaiBot完成重启]
```

## 注意事项

请确保启用了WebUI，否则无法重启。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。  

Copyright © 2026 lnrh1
