# MaiBot自动重启插件

提供阈值触发重启和定时重启功能

## 功能

- 监测CPU占用，超过设定阈值则重启MaiBot

- 监测内存占用，超过设定阈值则重启MaiBot

- 定时重启，到达设定时间时自动重启MaiBot

- 手动重启，发送 **/restart** 手动重启MaiBot

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

## 命令

```context
/restart
```

手动触发重启

```context
/restart_status
```

查看插件状态

## 重启原理

触发重启后，插件会获取用户的Access Token用于构造请求，这通常是安全的（因为插件不会向外部发送含有Access Token的信息且插件与MaiBot位于同一设备上，请求会到达本地WebUI）。随后向WebUI发送请求，MaiBot将自动完成重启。

```mermaid
获取Access Token -> 构造并发送重启请求 -> MaiBot自动完成重启
```

## 注意事项

请确保启用了WebUI，否则无法重启。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。  

Copyright © 2026 lnrh1
