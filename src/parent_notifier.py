"""
家长通知模块
负责在危机事件发生时通知家长/监护人
"""

from typing import Optional, Dict, List
from datetime import datetime
import json
import os


class ParentNotifier:
    """家长通知系统"""
    
    def __init__(self):
        self.notification_log: List[Dict] = []
        self.parent_contacts = self._load_parent_contacts()
    
    def _load_parent_contacts(self) -> Dict:
        """加载家长联系人配置"""
        return {
            "email": os.getenv("PARENT_EMAIL", ""),
            "phone": os.getenv("PARENT_PHONE", ""),
            "webhook_url": os.getenv("PARENT_WEBHOOK", ""),
            "enabled_methods": ["log", "display"]
        }
    
    def notify(
        self,
        alert_type: str,
        message: str,
        session_id: str = None,
        user_input: str = None,
        severity: str = "high"
    ) -> Dict:
        """
        发送通知给家长
        
        Args:
            alert_type: 警报类型 (self_harm, abuse, danger, etc.)
            message: 通知消息
            session_id: 会话ID
            user_input: 用户原始输入
            severity: 严重程度
            
        Returns:
            通知结果字典
        """
        notification = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "severity": severity,
            "session_id": session_id,
            "message": message,
            "user_input_preview": user_input[:100] if user_input else None,
            "status": "logged",
            "delivery_methods": []
        }
        
        notification["delivery_methods"].append("log")
        
        self.notification_log.append(notification)
        
        self._save_to_file(notification)
        
        return notification
    
    def _save_to_file(self, notification: Dict):
        """保存通知到文件"""
        log_dir = "logs/parent_notifications"
        os.makedirs(log_dir, exist_ok=True)
        
        filename = f"{log_dir}/notification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(notification, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save notification: {e}")
    
    def get_pending_notifications(self) -> List[Dict]:
        """获取待处理的通知"""
        return [n for n in self.notification_log if n.get("status") == "logged"]
    
    def get_notification_history(self, limit: int = 50) -> List[Dict]:
        """获取通知历史"""
        return self.notification_log[-limit:]
    
    def mark_as_reviewed(self, notification_id: str) -> bool:
        """标记通知为已查看"""
        for notification in self.notification_log:
            if notification.get("id") == notification_id:
                notification["status"] = "reviewed"
                notification["reviewed_at"] = datetime.now().isoformat()
                return True
        return False
    
    def generate_alert_summary(self, alert_type: str, user_input: str) -> str:
        """
        生成警报摘要
        
        Args:
            alert_type: 警报类型
            user_input: 用户输入
            
        Returns:
            警报摘要文本
        """
        summaries = {
            "self_harm": """
🚨 重要通知：检测到潜在的自我伤害风险

时间：{timestamp}
类型：自我伤害风险
严重程度：高

建议行动：
1. 立即与孩子沟通
2. 联系专业心理健康服务
3. 香港撒玛利亚防止自杀会：2389 2222

请及时关注孩子的情绪状态。
""",
            "abuse": """
🚨 重要通知：检测到潜在的虐待情况

时间：{timestamp}
类型：虐待风险
严重程度：高

建议行动：
1. 与孩子私下沟通了解情况
2. 联系防止虐待儿童会：2755 1522
3. 必要时联系社会福利署：2343 2255

请谨慎处理，确保孩子安全。
""",
            "danger_to_others": """
⚠️ 通知：检测到情绪极度激动

时间：{timestamp}
类型：情绪危机
严重程度：中高

建议行动：
1. 与孩子沟通，了解情绪来源
2. 考虑寻求专业辅导
3. 确保环境安全

请关注孩子的情绪调节。
"""
        }
        
        summary_template = summaries.get(alert_type, """
⚠️ 通知：检测到需要关注的情况

时间：{timestamp}
类型：{alert_type}

建议与孩子沟通了解情况。
""")
        
        return summary_template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            alert_type=alert_type
        )


class SessionLogger:
    """会话日志记录器 - 供家长/监护人审查"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def start_session(self, session_id: str, user_id: str = "default") -> Dict:
        """开始新会话"""
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "start_time": datetime.now().isoformat(),
            "messages": [],
            "safety_events": [],
            "metadata": {}
        }
        self.sessions[session_id] = session
        return session
    
    def log_message(
        self,
        session_id: str,
        role: str,
        content: str,
        safety_check: Dict = None
    ):
        """记录消息"""
        if session_id not in self.sessions:
            self.start_session(session_id)
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "safety_check": safety_check
        }
        
        self.sessions[session_id]["messages"].append(message)
        
        if safety_check and safety_check.get("flagged"):
            self.sessions[session_id]["safety_events"].append({
                "timestamp": message["timestamp"],
                "type": safety_check.get("type"),
                "severity": safety_check.get("severity")
            })
    
    def log_safety_event(
        self,
        session_id: str,
        event_type: str,
        severity: str,
        details: Dict = None
    ):
        """记录安全事件"""
        if session_id not in self.sessions:
            return
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "severity": severity,
            "details": details
        }
        
        self.sessions[session_id]["safety_events"].append(event)
    
    def end_session(self, session_id: str) -> Optional[Dict]:
        """结束会话"""
        if session_id not in self.sessions:
            return None
        
        self.sessions[session_id]["end_time"] = datetime.now().isoformat()
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def get_session_transcript(self, session_id: str) -> str:
        """获取会话转录"""
        session = self.sessions.get(session_id)
        if not session:
            return ""
        
        lines = []
        lines.append(f"Session ID: {session_id}")
        lines.append(f"Start Time: {session.get('start_time')}")
        lines.append("-" * 50)
        
        for msg in session.get("messages", []):
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"[{role}]: {content}")
        
        if session.get("safety_events"):
            lines.append("-" * 50)
            lines.append("SAFETY EVENTS:")
            for event in session["safety_events"]:
                lines.append(f"  - {event.get('type')}: {event.get('severity')}")
        
        return "\n".join(lines)
    
    def export_session(self, session_id: str) -> Optional[str]:
        """导出会话为 JSON"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        return json.dumps(session, ensure_ascii=False, indent=2)


parent_notifier = ParentNotifier()
session_logger = SessionLogger()
