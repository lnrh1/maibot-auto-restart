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

**管理员用户 ID 列表**，用于校验 **/restart** 命令的发起者身份。为空则不校验。默认为空。



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

手动触发重启。admin_ids 为空时所有成员可用；配置后仅管理员与本地控制台操作员可用，未授权成员会收到拒绝提示

```context
/restart_status
```

查看插件状态

## 权限与安全说明

- **/restart** 与 **trigger_restart** 动作都会触发 MaiBot 实际重启，造成服务短暂中断，因此插件提供 **admin_ids** 管理员校验：
  
  - 默认（空列表）**不校验**，所有成员均可使用 /restart。如需限制，请显式配置 admin_ids；
  
  - 配置后，仅列表内用户与本地控制台操作员可触发重启；未授权调用会被拒绝、记录主程序日志并回复提示；
  
  - **/restart_status** 只读取插件状态，不会触发重启，因此不做校验。

- 校验基于 MaiBot 宿主传入的**用户 ID**（user_id），对 MaiBot 接入的全部平台通用，不限于 QQ；不同平台上的同一 ID 会视为同一管理员。

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
