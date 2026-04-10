"""
安全事件日志记录器
负责持久化存储安全事件，供家长/监护人审查
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class SafetyEventType(Enum):
    SAFETY_FLAG = "safety_flag"
    CRISIS_DETECTED = "crisis_detected"
    INPUT_FILTERED = "input_filtered"
    OUTPUT_FILTERED = "output_filtered"


class SafetyEventStatus(Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"


class SafetyLogger:
    """安全事件日志记录器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.events_file = os.path.join(log_dir, "safety_events.json")
        self._ensure_log_dir()
        self._ensure_events_file()
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        os.makedirs(self.log_dir, exist_ok=True)
    
    def _ensure_events_file(self):
        """确保事件文件存在"""
        if not os.path.exists(self.events_file):
            self._write_events([])
    
    def _read_events(self) -> List[Dict]:
        """读取所有事件"""
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _write_events(self, events: List[Dict]):
        """写入所有事件"""
        with open(self.events_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
    
    def log_event(
        self,
        event_type: str,
        scenario: str,
        details: str,
        action_taken: str = "none",
        session_id: str = None,
        user_input_preview: str = None,
        emotion: str = "neutral",
        extra_data: Dict = None
    ) -> Dict:
        """
        记录安全事件
        
        Args:
            event_type: 事件类型 (safety_flag, crisis_detected, input_filtered)
            scenario: 触发场景
            details: 详细描述
            action_taken: 采取的行动
            session_id: 会话ID
            user_input_preview: 用户输入预览
            emotion: 情绪状态
            extra_data: 额外数据
            
        Returns:
            记录的事件字典
        """
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "scenario": scenario,
            "details": details,
            "action_taken": action_taken,
            "status": SafetyEventStatus.PENDING.value,
            "session_id": session_id,
            "user_input_preview": user_input_preview[:100] if user_input_preview else None,
            "emotion": emotion,
            "extra_data": extra_data or {},
            "reviewed_at": None,
            "reviewed_by": None
        }
        
        events = self._read_events()
        events.append(event)
        self._write_events(events)
        
        return event
    
    def get_events(
        self,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取事件列表
        
        Args:
            status: 筛选状态 (pending, reviewed, None表示全部)
            event_type: 筛选类型
            limit: 返回数量限制
            
        Returns:
            事件列表
        """
        events = self._read_events()
        
        if status:
            events = [e for e in events if e.get("status") == status]
        
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return events[:limit]
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """根据ID获取事件"""
        events = self._read_events()
        for event in events:
            if event.get("id") == event_id:
                return event
        return None
    
    def mark_reviewed(self, event_id: str, reviewed_by: str = "parent") -> bool:
        """
        标记事件为已处理
        
        Args:
            event_id: 事件ID
            reviewed_by: 处理人
            
        Returns:
            是否成功
        """
        events = self._read_events()
        
        for event in events:
            if event.get("id") == event_id:
                event["status"] = SafetyEventStatus.REVIEWED.value
                event["reviewed_at"] = datetime.now().isoformat()
                event["reviewed_by"] = reviewed_by
                self._write_events(events)
                return True
        
        return False
    
    def get_stats(self, days: int = 7) -> Dict:
        """
        获取统计数据
        
        Args:
            days: 统计天数
            
        Returns:
            统计字典
        """
        events = self._read_events()
        
        cutoff = datetime.now()
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        recent_events = [e for e in events if e.get("timestamp", "") >= cutoff_str]
        
        pending_count = len([e for e in recent_events if e.get("status") == "pending"])
        reviewed_count = len([e for e in recent_events if e.get("status") == "reviewed"])
        
        type_counts = {}
        for event in recent_events:
            et = event.get("event_type", "unknown")
            type_counts[et] = type_counts.get(et, 0) + 1
        
        return {
            "total": len(recent_events),
            "pending": pending_count,
            "reviewed": reviewed_count,
            "by_type": type_counts
        }
    
    def export_events(self, format: str = "json") -> str:
        """
        导出事件
        
        Args:
            format: 导出格式 (json, csv)
            
        Returns:
            导出的数据字符串
        """
        events = self._read_events()
        
        if format == "json":
            return json.dumps(events, ensure_ascii=False, indent=2)
        elif format == "csv":
            import io
            output = io.StringIO()
            
            if events:
                headers = ["timestamp", "event_type", "scenario", "details", "status", "action_taken"]
                output.write(",".join(headers) + "\n")
                
                for event in events:
                    row = [
                        event.get("timestamp", ""),
                        event.get("event_type", ""),
                        event.get("scenario", ""),
                        f'"{event.get("details", "")}"',
                        event.get("status", ""),
                        event.get("action_taken", "")
                    ]
                    output.write(",".join(row) + "\n")
            
            return output.getvalue()
        
        return ""
    
    def clear_old_events(self, days: int = 30) -> int:
        """
        清理旧事件
        
        Args:
            days: 保留天数
            
        Returns:
            删除的事件数量
        """
        events = self._read_events()
        
        cutoff = datetime.now()
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        new_events = [e for e in events if e.get("timestamp", "") >= cutoff_str]
        removed_count = len(events) - len(new_events)
        
        if removed_count > 0:
            self._write_events(new_events)
        
        return removed_count


safety_logger = SafetyLogger()
