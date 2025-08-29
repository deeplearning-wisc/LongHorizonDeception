# CODING.md

DeceptioN项目编码规范和状态跟踪

## 当前文件状态

DeceptioN/
├── main.py [Clean] - 完成完美主义优化：类型注解、常量定义、错误处理
├── core/
│   ├── Universal_LLM_Handler.py [CRITICAL UPDATE] - 完成overflow_truncate参数设计
│   ├── manager.py [Updated] - 添加overflow_truncate=False确保完整数据  
│   └── memory.py [Updated] - 添加overflow_truncate=False确保完整数据
├── tasks/
│   ├── task.py [Clean] - 完成架构重构和术语统一
│   └── event.py [Clean] - 完成EventSystem精简和无用方法清理
├── configs/
│   ├── api_profiles.yaml [NEW] - OpenRouter和Azure模型配置
│   └── test.yaml [Clean] - 术语已统一

## 编码标准

### 必须遵守的规范
- **类型注解**: 所有函数必须有完整类型注解
- **常量定义**: 禁止硬编码字符串，在文件顶部定义常量
- **错误处理**: 禁止print+continue，必须抛出明确异常
- **术语一致**: 使用JSON schema定义的标准字段名
- **严禁.get()默认值**: 绝对不允许使用.get(key, default)，必须严格键检查
- **严禁截断**: 除debug信息外，绝不截断任何科研数据
- **Fail-Fast**: 任何异常情况立即失败，不允许容错或妥协

### 核心术语规范

**任务相关**:
- `task_sequence_num` - 任务序列号（1-based）
- `total_tasks` - 总任务数

**事件相关**:  
- `pressure_level` - 压力级别（LOW/MEDIUM/HIGH/CRITICAL）
- `category` - 事件类别
- `event_name` - 事件名称（避免与其他name混淆）

**控制参数**:
- `control_category` - 类别控制："UNCONTROL"或具体类别
- `control_pressure_level` - 压力控制："UNCONTROL"或具体级别

### 禁用术语
- ❌ `task_idx`, `task_id` → ✅ `task_sequence_num`
- ❌ `pressure`, `intensity` → ✅ `pressure_level`
- ❌ `max_tasks` → ✅ `total_tasks`

### overflow_truncate参数设计
- **参数作用**: 控制LLM处理输入溢出的行为
- **严格模式** (`overflow_truncate=False`): Manager/Memory/Detector必须使用，超限直接报错
  - Azure: 传`"truncation": "disabled"`（默认值，显式禁用，超限报400）
  - OpenRouter: 传`"transforms": []`明确禁用middle-out
- **自动处理模式** (`overflow_truncate=True`): 一般LLM默认使用
  - Azure: 传`"truncation": "auto"`（启用中段压缩）
  - OpenRouter: 传`"transforms": ["middle-out"]`（启用中段压缩）

## 系统架构原则

- **Fail-fast**: 严格错误处理，确保数据完整性
- **职责分离**: TaskLoader管理任务和phase，EventSystem管理事件
- **可重现**: 通过seed控制随机性，支持科学实验对于上一轮来说,我希望你好好检查有没有fallback,有没有截断,反正就是那个markdown文档里说的那点东西