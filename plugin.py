import asyncio
import psutil
import aiohttp
from datetime import datetime
from typing import List

from maibot_sdk import MaiBotPlugin, Command, Action, CONFIG_RELOAD_SCOPE_SELF, Field, PluginConfigBase


class PluginSection(PluginConfigBase):
    
    __ui_label__ = "基础设置"
    __ui_order__ = 0
    
    config_version: str = Field(
        default="1.1",
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


class AdminConfig(PluginConfigBase):
    
    __ui_label__ = "权限设置"
    __ui_order__ = 3
    
    admin_ids: List[str] = Field(
        default_factory=list,
        description="管理员用户 ID 列表",
        json_schema_extra={
            "placeholder": "1234567890"
        }
    )


class AdvancedConfig(PluginConfigBase):
    
    __ui_label__ = "高级设置"
    __ui_order__ = 4
    
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

    access_token: str = Field(
        default="",
        description="WebUI访问令牌"
    )


class MaiBotAutoRestartConfig(PluginConfigBase):
    
    plugin: PluginSection = Field(default_factory=PluginSection)
    threshold: ThresholdConfig = Field(default_factory=ThresholdConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)


class MaiBotAutoRestart(MaiBotPlugin):
    
    config_model = MaiBotAutoRestartConfig
    
    def __init__(self):
        super().__init__()
        self.restart_tasks: list = []
        self.monitor_running = False
        
    async def on_load(self) -> None:
        self.ctx.logger.info("[lnrh1.maibot_auto_restart] 插件加载成功")
        
        await self._setup_schedule_restart()
        
        if self.config.threshold.enable_threshold_monitor:
            await self._start_threshold_monitor()
            
        admin_ids = self._get_admin_ids()
        if admin_ids:
            self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 管理员校验已启用，已配置 {len(admin_ids)} 个管理员 ID")
        else:
            self.ctx.logger.warning("[lnrh1.maibot_auto_restart] 未配置管理员 ID，/restart 对所有成员可用；如需限制请在权限设置中填写 admin_ids")
        
        self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 配置加载完成")
    
    async def on_unload(self) -> None:
       
        self.ctx.logger.info("[lnrh1.maibot_auto_restart] 插件卸载中...")
        
        self.monitor_running = False
        
        for task in self.restart_tasks:
            if not task.done():
                task.cancel()
                
        self.ctx.logger.info("[lnrh1.maibot_auto_restart] 插件卸载完成")
    
    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 配置已更新：version={version}")
    
    async def _setup_schedule_restart(self) -> None:
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
    
    async def _get_access_token(self) -> str:
        token = self.config.advanced.access_token
        if not token:
            raise RuntimeError(
                "未配置 Access Token，请在插件高级设置中填写 access_token。"
            )
        return token
    
    def _get_admin_ids(self) -> List[str]:
        return [str(item).strip().lower() for item in self.config.admin.admin_ids if str(item).strip()]
    
    def _is_privileged(self, user_id: str, is_local_operator: bool) -> bool:
        admin_ids = self._get_admin_ids()
        if not admin_ids:
            return True
        
        if is_local_operator:
            return True
        
        user_key = str(user_id or "").strip().lower()
        if not user_key:
            return False
        
        return any(entry == user_key for entry in admin_ids)
    
    async def _trigger_restart(self, reason: str = "手动重启", stream_id: str = None) -> None:

        self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 触发重启，原因：{reason}")
        
        delay = self.config.advanced.restart_delay_seconds
        port = self.config.advanced.webui_port
        
        if self.config.advanced.notify_before_manual_restart and stream_id:
            try:
                await self.ctx.send.text(f"系统将在 {delay} 秒后重启，原因：{reason}", stream_id)
            except Exception as e:
                self.ctx.logger.warning(f"[lnrh1.maibot_auto_restart] 发送通知失败：{e}")
        
        await asyncio.sleep(delay)
        
        self.ctx.logger.info(f"[lnrh1.maibot_auto_restart] 调用 WebUI 重启 API (端口：{port})")
        
        try:
            token = await self._get_access_token()
            
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
        stream_id = kwargs.get("stream_id")
        platform = kwargs.get("platform", "")
        user_id = kwargs.get("user_id", "")
        is_local_operator = kwargs.get("is_local_operator") is True
        
        if not self._is_privileged(user_id, is_local_operator):
            self.ctx.logger.warning(
                f"[lnrh1.maibot_auto_restart] 拒绝未授权的重启请求: platform={platform} user_id={user_id}"
            )
            await self.ctx.send.text("你没有权限执行 /restart 命令，该操作仅限管理员使用", stream_id)
            return False, "没有权限", 1
        
        await self._trigger_restart("手动命令触发", stream_id)
        return True, "重启指令已发送", 1
    
    @Command("restart_status", pattern=r"^/restart_status\s*$", description="查看重启配置状态")
    async def cmd_restart_status(self, **kwargs):
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
        return True, "状态已发送", 1
    
    @Action("trigger_restart", description="触发动作 - 手动触发重启")
    async def action_restart(self, **kwargs):
        platform = kwargs.get("platform", "")
        user_id = kwargs.get("user_id", "")
        is_local_operator = kwargs.get("is_local_operator") is True
        action_data = kwargs.get("action_data")
        if isinstance(action_data, dict) and "user_id" in action_data:
            user_id = ""
        
        if not self._is_privileged(user_id, is_local_operator):
            self.ctx.logger.warning(
                f"[lnrh1.maibot_auto_restart] 拒绝未授权的重启动作: platform={platform} user_id={user_id}"
            )
            return False, "没有权限执行重启动作，该操作仅限管理员使用"
        
        await self._trigger_restart("动作触发")
        return True, "重启已触发"


def create_plugin():
    return MaiBotAutoRestart()
