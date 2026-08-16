# MaiBot自动重启插件

提供阈值触发重启和定时重启功能

## 功能

* 监测CPU占用，超过设定阈值则重启MaiBot
  
* 监测内存占用，超过设定阈值则重启MaiBot
  
* 定时重启，到达设定时间时自动重启MaiBot
  
* 手动重启，发送 **/restart** 手动重启MaiBot
  

## 安装

### 方式一

在MaiBot插件市场中搜索并安装本插件。

### 方式二

手动克隆本插件至插件目录。

    cd /root/MaiBot/plugins
    git clone https://github.com/lnrh1/maibot-auto-restart.git

## 配置

    enable_threshold_monitor = true

**是否启用阈值监测**，为false则禁用阈值监测，为true则启用阈值监测。默认为true.

    memory_threshold_percent = 80

**内存阈值百分比**，若监测到的内存占用超过设定值，则触发重启。默认为80.

    cpu_threshold_percent = 90

**CPU阈值百分比**，若监测到的CPU占用超过设定值，则触发重启。默认为90.

    enable_schedule_restart = false

**是否启用定时重启**，为false则禁用定时重启，为true则启用定时重启。默认为false.

    restart_time = "04:00"

**定时重启时间**，采用24小时制，格式为 HH:MM 。到达该时间则触发重启。默认为"04:00".

    restart_delay_seconds = 5

**重启前延迟秒数**，触发重启前将等待该时长后再执行重启。默认为5.

    notify_before_manual_restart = true

**手动重启前是否发送通知**，为false则手动重启时不发送通知，为true则手动重启时发送通知。默认为true.

    webui_port = 8001

**WebUI端口**，用于发送重启请求。默认为8001.

## 命令

    /restart

手动触发重启

    /restart_status

查看插件状态

## 重启原理

触发重启时，插件将利用Access Token构造请求,随后发送该请求至本地WebUI，MaiBot将自动重启。

    获取Access Token -> 构造并发送重启请求 -> MaiBot自动完成重启

## 注意事项

请确保启用了WebUI，否则无法重启。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

Copyright © 2026 lnrh1
