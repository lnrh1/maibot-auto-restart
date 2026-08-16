import asyncio
import psutil
import aiohttp
from datetime import datetime

from maibot_sdk import MaiBotPlugin, Command, Action, CONFIG_RELOAD_SCOPE_SELF, Field, PluginConfigBase


class PluginSection(PluginConfigBase):
    
    __ui_label__ = "基础设置"
    __ui_order__ = 0
    
    config_version: str = Field(
        default="1.0",
        description="配置文件版本"
    )


class ThresholdConfig(PluginConfigBase):
    
    __ui_label__ = "阈值监控"
    __ui_order__ = 1
    
    enable_threshold_monitor: bool = Field(
        default=True,
        description="是否启用阈值监控"
    )
    
    memory_threshold_percent: int = Field(
        default=80,
        description="内存阈值百分比（%）",
        json_schema_extra={
            "min": 1,
            "max": 100,
            "step": 1
        }
    )
    
    cpu_threshold_percent: int = Field(
        default=90,
        description="CPU 阈值百分比（%）",
        json_schema_extra={
            "min": 1,
            "max": 100,
            "step": 1
        }
    )


class ScheduleConfig(PluginConfigBase):
    
    __ui_label__ = "定时重启"
    __ui_order__ = 2
    
    enable_schedule_restart: bool = Field(
        default=False,
        description="是否启用定时重启"
    )
    
    restart_time: str = Field(
        default="04:00",
        description="定时重启时间（24 小时制，格式：HH:MM）",
        json_schema_extra={
            "placeholder": "04:00"
        }
    )


class AdvancedConfig(PluginConfigBase):
    
    __ui_label__ = "高级设置"
    __ui_order__ = 3
    
    restart_delay_seconds: int = Field(
        default=5,
        description="重启前延迟秒数",
        json_schema_extra={
            "min": 0,
            "max": 60,
            "step": 1
        }
    )
    
    notify_before_manual_restart: bool = Field(
        default=True,
        description="手动重启前是否发送通知"
    )
    
    webui_port: int = Field(
        default=8001,
        description="MaiBot WebUI 端口号",
        json_schema_extra={
            "min": 1,
            "max": 65535
        }
    )

    webui_token: str = Field(
    default="",
    description="WebUI访问令牌"
    )


class MaiBotAutoRestartConfig(PluginConfigBase):
    
    plugin: PluginSection = Field(default_factory=PluginSection)
    threshold: ThresholdConfig = Field(default_factory=ThresholdConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)


class MaiBotAutoRestart(MaiBotPlugin):
    
    config_model = MaiBotAutoRestartConfig
    
    def __init__(self):
        super().__init__()
        self.restart_tasks: list = []
        self.monitor_running = False
        
    async def on_load(self) -> None:
        """插件加载时执行"""
        self.ctx.logger.info("[lnrh1.maibot_auto_restart] 插件加载成功")
        
        # 启动定时重启任务
        await self._setup_schedule_restart()
        
        # 启动阈值监控
        if self.config.threshold.enable_threshold_monitor:
            await self._start_threshold_monitor()
            
        self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 配置加载完成")
    
    async def on_unload(self) -> None:
       
        self.ctx.logger.info("[lnrh1.maibot_auto_restart] 插件卸载中...")
        
        self.monitor_running = False
        
        for task in self.restart_tasks:
            if not task.done():
                task.cancel()
                
        self.ctx.logger.info("[lnrh1.maibot_auto_restart] 插件卸载完成")
    
    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        """配置更新时执行"""
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 配置已更新：version={version}")
    
    async def _setup_schedule_restart(self) -> None:
        """设置定时重启任务"""
        if not self.config.schedule.enable_schedule_restart:
            return
            
        restart_time = self.config.schedule.restart_time
        
        try:
            hour, minute = map(int, restart_time.split(":"))
            
            async def schedule_loop():
                self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 定时重启任务已启动，目标时间：{restart_time}")
                
                while True:
                    now = datetime.now()
                    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if now >= target:
                        from datetime import timedelta
                        target = target + timedelta(days=1)
                    
                    wait_seconds = (target - now).total_seconds()
                    
                    self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 下次重启时间：{target}, 等待 {wait_seconds} 秒")
                    
                    await asyncio.sleep(wait_seconds)
                    await self._trigger_restart("定时重启")
            
            task = asyncio.create_task(schedule_loop())
            self.restart_tasks.append(task)
            
        except Exception as e:
            self.ctx.logger.error(f"[lnrh1.maibot_auto_restart] 设置定时重启失败：{e}")
    
    async def _start_threshold_monitor(self) -> None:
        """启动阈值监控"""
        self.monitor_running = True
        
        async def monitor_loop():
            self.ctx.logger.info("[lnrh1.maibot_auto_restart] 阈值监控已启动")
            
            while self.monitor_running:
                try:
                    memory_percent = psutil.virtual_memory().percent
                    memory_threshold = self.config.threshold.memory_threshold_percent
                    
                    if memory_percent >= memory_threshold:
                        self.ctx.logger.warning(f"[lnrh1.maibot_auto_restart] 内存超限：{memory_percent:.2f}% > {memory_threshold}%")
                        await self._trigger_restart(f"内存超限 ({memory_percent:.2f}%)")
                        break
                    
                    cpu_percent = psutil.cpu_percent(interval=1)
                    cpu_threshold = self.config.threshold.cpu_threshold_percent
                    
                    if cpu_percent >= cpu_threshold:
                        self.ctx.logger.warning(f"[lnrh1.maibot_auto_restart] CPU超限：{cpu_percent}% > {cpu_threshold}%")
                        await self._trigger_restart(f"CPU超限 ({cpu_percent}%)")
                        break
                    
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    self.ctx.logger.error(f"[lnrh-maibot_auto_restart] 监控循环错误：{e}")
                    await asyncio.sleep(60)
        
        task = asyncio.create_task(monitor_loop())
        self.restart_tasks.append(task)
    
    async def _get_webui_token(self) -> str:
        token = self.config.advanced.webui_token
        if not token:
            raise RuntimeError(
                "未配置 WebUI token，请在插件高级设置中填写 webui_token。"
            )
        return token
    
    async def _trigger_restart(self, reason: str = "手动重启", stream_id: str = None) -> None:

        self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 触发重启，原因：{reason}")
        
        delay = self.config.advanced.restart_delay_seconds
        port = self.config.advanced.webui_port
        
        if self.config.advanced.notify_before_manual_restart and stream_id:
            try:
                await self.ctx.send.text(f"系统将在 {delay} 秒后重启，原因：{reason}", stream_id)
            except Exception as e:
                self.ctx.logger.warning(f"[lnrh1.maibot_auto_restart] 发送通知失败：{e}")
        
        # 等待延迟
        await asyncio.sleep(delay)
        
        # 调用 WebUI 重启 API
        self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 调用 WebUI 重启 API (端口：{port})")
        
        try:
            # 读取 WebUI token
            token = await self._get_webui_token()
            
            async with aiohttp.ClientSession() as session:
                url = f"http://127.0.0.1:{port}/api/webui/system/restart"
                headers = {"Cookie": f"maibot_session={token}"}
                async with session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        self.ctx.logger.info(f"[lnrh-maibot_auto_restart] WebUI 重启 API 调用成功")
                    else:
                        self.ctx.logger.warning(f"[lnrh-maibot_auto_restart] WebUI 重启 API 返回状态码：{resp.status}")
        except Exception as e:
            self.ctx.logger.error(f"[lnrh-maibot_auto_restart] 调用 WebUI 重启 API 失败：{e}")
            self.ctx.logger.warning(f"[lnrh-maibot_auto_restart] 重启失败，请手动重启或通过 WebUI 重启")
    
    @Command("restart", pattern=r"^/restart\s*$", description="手动触发重启")
    async def cmd_restart(self, **kwargs):
        """手动重启命令"""
        stream_id = kwargs.get("stream_id")
        await self._trigger_restart("手动命令触发", stream_id)
        return True, "重启指令已发送"
    
    @Command("restart_status", pattern=r"^/restart_status\s*$", description="查看重启配置状态")
    async def cmd_restart_status(self, **kwargs):
        """查看重启配置状态"""
        stream_id = kwargs.get("stream_id")
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=1)
        
        status_msg = (
            "自动重启插件状态\n"
            "====================\n\n"
            f"阈值监控：{'开启' if self.config.threshold.enable_threshold_monitor else '关闭'}\n"
            f"内存阈值：{self.config.threshold.memory_threshold_percent}% (当前：{memory_percent:.1f}%)\n"
            f"CPU 阈值：{self.config.threshold.cpu_threshold_percent}% (当前：{cpu_percent:.1f}%)\n\n"
            f"定时重启：{'开启' if self.config.schedule.enable_schedule_restart else '关闭'}\n"
            f"重启时间：{self.config.schedule.restart_time}\n"
            f"重启延迟：{self.config.advanced.restart_delay_seconds} 秒\n"
            f"WebUI 端口：{self.config.advanced.webui_port}\n"
        )
        
        await self.ctx.send.text(status_msg, stream_id)
        return True, "状态已发送"
    
    @Action("trigger_restart", description="触发动作 - 手动触发重启")
    async def action_restart(self,**kwargs):
        """动作 - 触发重启"""
        await self._trigger_restart("动作触发")
        return True, "重启已触发"


def create_plugin():
    """创建插件实例"""
    return MaiBotAutoRestart()
