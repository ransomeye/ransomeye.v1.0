# Phase-10: Core Runtime Reality Validation & Fix Design
**Independent Principal Systems Architect & Runtime Auditor Report**

**Date**: 2025-01-10  
**Auditor**: Independent Systems Architect  
**Scope**: Core Runtime Lifecycle, Component Execution, Dependency Ordering, Supervision & Failure Semantics

---

## Executive Verdict

**SHIP-BLOCKER**

Core Runtime does **NOT** execute or orchestrate components. It loads modules and enters a sleep loop. Components are never started, dependencies are not enforced, and there is no supervision mechanism. The system cannot operate at a customer site without manual intervention.

---

## 1. Exact Findings

### 1.1 Core Runtime Execution Model

**Location**: `core/runtime.py:634-661`

**Current Behavior**:
```python
def run_core():
    _initialize_core()           # Lines 639-640: Validates environment, DB, schema
    _load_component_modules()     # Lines 642-643: Imports modules only
    logger.startup("Core runtime ready")  # Line 651
    
    # Lines 656-658: Sleep loop - NO component execution
    import time
    while not _shutdown_handler.is_shutdown_requested():
        time.sleep(1)
```

**Evidence**:
- **Line 595-632**: Components are imported as modules (`import main as ingest_main`)
- **Line 651**: Core logs "ready" but components are never started
- **Lines 656-658**: Core enters infinite sleep loop
- **NOT IMPLEMENTED**: No calls to component `run_*()` functions
- **NOT IMPLEMENTED**: No component lifecycle management

**Component Entry Points That Exist But Are Never Called**:
- `services/correlation-engine/app/main.py:210` - `run_correlation_engine()`
- `services/ai-core/app/main.py:95` - `run_ai_core()`
- `services/policy-engine/app/main.py:200` - `run_policy_engine()`
- `services/ingest/app/main.py:919-923` - `uvicorn.run()` (FastAPI service)
- `services/ui/backend/main.py:646-650` - `uvicorn.run()` (FastAPI service)

### 1.2 Component State Tracking (Unused)

**Location**: `core/runtime.py:108-114`

**Current State**:
```python
_component_state = {
    'ingest': {'running': False, 'conn': None},
    'correlation': {'running': False, 'conn': None},
    'ai_core': {'running': False, 'conn': None},
    'policy': {'running': False, 'conn': None},
    'ui': {'running': False, 'conn': None}
}
```

**Evidence**:
- **Line 109-113**: State dictionary exists with `running` flags
- **Line 526, 543**: State is set to `False` during shutdown
- **NOT IMPLEMENTED**: State is **never** set to `True`
- **NOT IMPLEMENTED**: No code checks `running` status
- **NOT IMPLEMENTED**: No health monitoring uses this state

### 1.3 Component Lifecycle Analysis

#### Ingest Service
- **Location**: `services/ingest/app/main.py:919-923`
- **Start Method**: `uvicorn.run(app, host="0.0.0.0", port=port)` when run as `__main__`
- **Health Check**: `/health` endpoint exists (line 900-917)
- **Failure Handling**: FastAPI exception handlers, but Core never starts the service
- **Shutdown Handling**: FastAPI shutdown event (line 361-364), but Core never triggers it
- **Status**: **NOT STARTED BY CORE**

#### Correlation Engine
- **Location**: `services/correlation-engine/app/main.py:210-296`
- **Start Method**: `run_correlation_engine()` function
- **Health Check**: **NOT IMPLEMENTED** - No health check function
- **Failure Handling**: Exceptions logged, continues processing (line 265-277)
- **Shutdown Handling**: Checks `shutdown_handler.is_shutdown_requested()` (line 251)
- **Status**: **NOT STARTED BY CORE**

#### AI Core
- **Location**: `services/ai-core/app/main.py:95-457`
- **Start Method**: `run_ai_core()` function
- **Health Check**: **NOT IMPLEMENTED** - No health check function
- **Failure Handling**: Exceptions cause `exit_startup_error()` (line 130)
- **Shutdown Handling**: Checks `shutdown_handler.is_shutdown_requested()` (line 195)
- **Status**: **NOT STARTED BY CORE**

#### Policy Engine
- **Location**: `services/policy-engine/app/main.py:200-339`
- **Start Method**: `run_policy_engine()` function
- **Health Check**: **NOT IMPLEMENTED** - No health check function
- **Failure Handling**: Exceptions cause `exit_fatal()` (line 197)
- **Shutdown Handling**: **NOT IMPLEMENTED** - No shutdown check in main loop
- **Status**: **NOT STARTED BY CORE**

#### UI Backend
- **Location**: `services/ui/backend/main.py:646-650`
- **Start Method**: `uvicorn.run(app, host="0.0.0.0", port=port)` when run as `__main__`
- **Health Check**: `/health` endpoint exists (line 630-644)
- **Failure Handling**: FastAPI exception handlers, but Core never starts the service
- **Shutdown Handling**: FastAPI shutdown event, but Core never triggers it
- **Status**: **NOT STARTED BY CORE**

### 1.4 Dependency Enforcement

**Location**: `core/runtime.py:581-632`

**Current Behavior**:
- Components are loaded in arbitrary order (Ingest, Correlation, AI Core, Policy, UI)
- **NOT IMPLEMENTED**: No dependency graph definition
- **NOT IMPLEMENTED**: No dependency ordering enforcement
- **NOT IMPLEMENTED**: No dependency health checks before starting dependents

**Required Dependency Order** (inferred from data flow):
1. **Database** (must be available first)
2. **Ingest** (no dependencies on other components)
3. **Correlation Engine** (depends on Ingest producing events)
4. **AI Core** (depends on Correlation Engine producing incidents)
5. **Policy Engine** (depends on Correlation Engine producing incidents)
6. **UI Backend** (depends on all components producing data)

**Evidence**:
- **Line 588-592**: Paths added to `sys.path` in arbitrary order
- **Line 594-632**: Modules imported in arbitrary order
- **NOT IMPLEMENTED**: No dependency validation
- **NOT IMPLEMENTED**: No startup sequence enforcement

### 1.5 Failure Semantics

**Location**: `core/runtime.py:634-661`

**Current Behavior**:
- **NOT IMPLEMENTED**: No supervision loop
- **NOT IMPLEMENTED**: No component health monitoring
- **NOT IMPLEMENTED**: No failure detection
- **NOT IMPLEMENTED**: No retry logic (as per requirements)
- **NOT IMPLEMENTED**: No degradation handling
- **NOT IMPLEMENTED**: No system shutdown on unrecoverable conditions

**What Should Happen** (per `contracts/failure-semantics.md`):
- **Component crash** (line 31): Should emit crash event, mark component as `FAILED`, trigger recovery
- **Dependencies unavailable** (line 17): Should emit dependency failure event, mark component as `DEGRADED` or `FAILED`
- **Resource exhaustion** (line 32): Should emit resource exhaustion event, mark component as `DEGRADED`, throttle processing

**Evidence**:
- **Lines 656-658**: Sleep loop with no supervision
- **NOT IMPLEMENTED**: No exception handlers around component execution
- **NOT IMPLEMENTED**: No health check polling
- **NOT IMPLEMENTED**: No failure state tracking

### 1.6 Installer Workaround (Contradicts Design)

**Location**: `installer/core/install.sh:350-356`

**Current Behavior**:
```bash
# Start Ingest service in background
python3 "${INSTALL_ROOT}/lib/services/ingest/app/main.py" &
INGEST_PID=$!

# Start UI Backend service in background
python3 "${INSTALL_ROOT}/lib/services/ui/backend/main.py" &
UI_PID=$!
```

**Evidence**:
- **Line 351**: Ingest started as separate process (contradicts "single Core runtime")
- **Line 355**: UI started as separate process (contradicts "single Core runtime")
- **Line 364**: Core started separately, does not coordinate these processes
- **Line 332-340**: Cleanup function kills background processes, but Core has no knowledge of them

**Impact**: Installer workaround masks the fact that Core does not execute components. This is a production risk because:
- Core cannot supervise these processes
- Core cannot detect if they crash
- Core cannot coordinate shutdown
- Systemd tracks Core process, but Ingest/UI are untracked background processes

---

## 2. Critical Gaps

### Gap 1: No Component Execution
- **Location**: `core/runtime.py:634-661`
- **Production Impact**: **CRITICAL** - System does not function. Components never start, so:
  - No events are ingested
  - No correlation occurs
  - No AI analysis happens
  - No policy evaluation occurs
  - No UI is available
- **Evidence**: Lines 656-658 show sleep loop with no component calls

### Gap 2: No Dependency Ordering
- **Location**: `core/runtime.py:581-632`
- **Production Impact**: **HIGH** - Even if components were started, they would start in wrong order:
  - Correlation Engine might start before Ingest (no events to process)
  - AI Core might start before Correlation Engine (no incidents to analyze)
  - Policy Engine might start before Correlation Engine (no incidents to evaluate)
- **Evidence**: No dependency graph or ordering logic exists

### Gap 3: No Supervision Loop
- **Location**: `core/runtime.py:656-658`
- **Production Impact**: **CRITICAL** - Core cannot detect or respond to failures:
  - Component crashes go undetected
  - Health degradation goes undetected
  - Resource exhaustion goes undetected
  - System operates in unknown state
- **Evidence**: Sleep loop with no monitoring

### Gap 4: No Health Checking
- **Location**: Multiple (see component analysis above)
- **Production Impact**: **HIGH** - Core cannot determine component health:
  - Cannot detect if Ingest is accepting requests
  - Cannot detect if Correlation Engine is processing events
  - Cannot detect if AI Core is analyzing incidents
  - Cannot detect if Policy Engine is evaluating policies
  - Cannot detect if UI is serving requests
- **Evidence**: Health endpoints exist for Ingest/UI but are never called by Core

### Gap 5: No Failure Handling
- **Location**: `core/runtime.py:634-661`
- **Production Impact**: **CRITICAL** - Failures cause silent degradation:
  - Component exceptions are not caught by Core
  - Component crashes do not trigger recovery
  - Dependency failures do not trigger degradation
  - Unrecoverable conditions do not trigger shutdown
- **Evidence**: No exception handlers around component execution

### Gap 6: Component State Never Updated
- **Location**: `core/runtime.py:108-114, 526, 543`
- **Production Impact**: **MEDIUM** - State tracking infrastructure exists but is unused:
  - Cannot query component status
  - Cannot determine if components are running
  - Cannot coordinate shutdown based on state
- **Evidence**: `running` flags are set to `False` but never to `True`

---

## 3. Minimum Correct Architecture

### 3.1 Required Lifecycle States

Each component must have explicit states:
- **UNINITIALIZED**: Component not loaded
- **LOADED**: Module imported, not started
- **STARTING**: Component initialization in progress
- **RUNNING**: Component executing normally
- **DEGRADED**: Component running but with reduced functionality
- **FAILED**: Component crashed or unrecoverable error
- **STOPPING**: Component shutdown in progress
- **STOPPED**: Component stopped

**Location**: Must be added to `core/runtime.py` component state management

### 3.2 Required Component Interface

All components must expose a standard interface:

```python
class ComponentInterface:
    def start(self) -> None:
        """Start component. Raises ComponentStartupError on failure."""
        pass
    
    def stop(self) -> None:
        """Stop component gracefully."""
        pass
    
    def health_check(self) -> ComponentHealth:
        """Check component health. Returns ComponentHealth enum."""
        pass
    
    def get_dependencies(self) -> List[str]:
        """Return list of component names this component depends on."""
        pass
```

**Location**: Must be created in `core/runtime.py` or new `core/component_interface.py`

### 3.3 Required Dependency Model

Core must maintain explicit dependency graph:

```python
DEPENDENCY_GRAPH = {
    'ingest': [],  # No dependencies
    'correlation': ['ingest'],  # Depends on Ingest
    'ai_core': ['correlation'],  # Depends on Correlation
    'policy': ['correlation'],  # Depends on Correlation
    'ui': ['ingest', 'correlation', 'ai_core', 'policy']  # Depends on all
}
```

**Location**: Must be added to `core/runtime.py`

### 3.4 Required Supervision Loop

Core must implement supervision loop that:
1. Starts components in dependency order
2. Monitors component health periodically
3. Detects component failures
4. Handles failures according to failure semantics contract
5. Coordinates graceful shutdown

**Location**: Must replace sleep loop in `core/runtime.py:656-658`

---

## 4. Concrete Fix Plan

### 4.1 Files That Must Change

#### File 1: `core/runtime.py`
**Changes Required**:
1. **Add Component Interface** (new class, ~50 lines)
   - Define `ComponentInterface` abstract base class
   - Define `ComponentHealth` enum (HEALTHY, DEGRADED, FAILED)
   - Define `ComponentState` enum (UNINITIALIZED, LOADED, STARTING, RUNNING, DEGRADED, FAILED, STOPPING, STOPPED)

2. **Add Dependency Graph** (new constant, ~10 lines)
   - Define `DEPENDENCY_GRAPH` dictionary
   - Define `STARTUP_ORDER` list (topological sort of dependencies)

3. **Add Component Wrappers** (new functions, ~200 lines)
   - `_create_component_wrapper(module, name)` - Wraps component modules with standard interface
   - `_start_component(component_name)` - Starts component, updates state
   - `_stop_component(component_name)` - Stops component, updates state
   - `_check_component_health(component_name)` - Checks component health

4. **Replace Sleep Loop with Supervision Loop** (modify `run_core()`, ~100 lines)
   - Start components in dependency order
   - Implement supervision loop that:
     - Polls component health every N seconds
     - Detects failures
     - Handles failures per failure semantics contract
     - Coordinates shutdown

5. **Add Failure Handling** (new functions, ~150 lines)
   - `_handle_component_failure(component_name, error)` - Handles component failures
   - `_should_retry(component_name, error)` - Determines if retry is appropriate (per contract: NO retries)
   - `_should_degrade(component_name, error)` - Determines if degradation is appropriate
   - `_should_shutdown(component_name, error)` - Determines if system shutdown is required

**Estimated Lines Changed**: ~510 lines added/modified

#### File 2: `services/ingest/app/main.py`
**Changes Required**:
1. **Expose Component Interface** (modify, ~30 lines)
   - Add `start()` function that calls `uvicorn.run()` in background thread
   - Add `stop()` function that stops uvicorn server
   - Add `health_check()` function that calls `/health` endpoint
   - Add `get_dependencies()` function returning `[]`

**Estimated Lines Changed**: ~30 lines added

#### File 3: `services/correlation-engine/app/main.py`
**Changes Required**:
1. **Expose Component Interface** (modify, ~40 lines)
   - Wrap `run_correlation_engine()` in `start()` function (run in thread)
   - Add `stop()` function that sets shutdown flag
   - Add `health_check()` function (check if processing loop is running)
   - Add `get_dependencies()` function returning `['ingest']`

**Estimated Lines Changed**: ~40 lines added

#### File 4: `services/ai-core/app/main.py`
**Changes Required**:
1. **Expose Component Interface** (modify, ~40 lines)
   - Wrap `run_ai_core()` in `start()` function (run in thread)
   - Add `stop()` function that sets shutdown flag
   - Add `health_check()` function (check if processing loop is running)
   - Add `get_dependencies()` function returning `['correlation']`

**Estimated Lines Changed**: ~40 lines added

#### File 5: `services/policy-engine/app/main.py`
**Changes Required**:
1. **Expose Component Interface** (modify, ~40 lines)
   - Wrap `run_policy_engine()` in `start()` function (run in thread)
   - Add `stop()` function that sets shutdown flag
   - Add `health_check()` function (check if processing loop is running)
   - Add `get_dependencies()` function returning `['correlation']`

**Estimated Lines Changed**: ~40 lines added

#### File 6: `services/ui/backend/main.py`
**Changes Required**:
1. **Expose Component Interface** (modify, ~30 lines)
   - Add `start()` function that calls `uvicorn.run()` in background thread
   - Add `stop()` function that stops uvicorn server
   - Add `health_check()` function that calls `/health` endpoint
   - Add `get_dependencies()` function returning `['ingest', 'correlation', 'ai_core', 'policy']`

**Estimated Lines Changed**: ~30 lines added

#### File 7: `installer/core/install.sh`
**Changes Required**:
1. **Remove Workaround** (modify, ~20 lines)
   - Remove lines 350-356 (background process starts)
   - Remove lines 328-329 (PID tracking)
   - Remove lines 332-340 (cleanup function)
   - Core will now start all components internally

**Estimated Lines Changed**: ~20 lines removed

**Total Estimated Changes**: ~710 lines added/modified/removed

### 4.2 New Abstractions Required

#### Abstraction 1: Component Interface
- **Location**: `core/runtime.py` or `core/component_interface.py`
- **Purpose**: Standard interface for all components
- **Methods**: `start()`, `stop()`, `health_check()`, `get_dependencies()`

#### Abstraction 2: Dependency Manager
- **Location**: `core/runtime.py`
- **Purpose**: Manage component dependencies and startup order
- **Functions**: `_get_startup_order()`, `_validate_dependencies()`, `_check_dependency_health()`

#### Abstraction 3: Supervision Loop
- **Location**: `core/runtime.py` (replace sleep loop)
- **Purpose**: Monitor component health and handle failures
- **Functions**: `_supervision_loop()`, `_poll_component_health()`, `_handle_component_failure()`

#### Abstraction 4: Failure Handler
- **Location**: `core/runtime.py`
- **Purpose**: Handle component failures per failure semantics contract
- **Functions**: `_should_retry()`, `_should_degrade()`, `_should_shutdown()`, `_handle_failure()`

---

## 5. Acceptance Criteria

Phase-10 is complete **only if** all of the following conditions are met:

### 5.1 Component Execution
- [ ] **AC1.1**: Core calls `start()` method on all components
- [ ] **AC1.2**: Components transition from LOADED → STARTING → RUNNING states
- [ ] **AC1.3**: Component `running` flags in `_component_state` are set to `True` when running
- [ ] **Evidence**: Add test that verifies `_component_state['ingest']['running'] == True` after startup

### 5.2 Dependency Ordering
- [ ] **AC2.1**: Core starts components in dependency order (Ingest → Correlation → AI Core/Policy → UI)
- [ ] **AC2.2**: Core waits for dependency health checks to pass before starting dependents
- [ ] **AC2.3**: Core fails to start if critical dependency (Database) is unavailable
- [ ] **Evidence**: Add test that verifies startup order matches dependency graph

### 5.3 Supervision Loop
- [ ] **AC3.1**: Core implements supervision loop (not sleep loop)
- [ ] **AC3.2**: Supervision loop polls component health every N seconds (configurable, default 30s)
- [ ] **AC3.3**: Supervision loop detects component failures within polling interval
- [ ] **Evidence**: Add test that verifies supervision loop calls `health_check()` on all components

### 5.4 Health Monitoring
- [ ] **AC4.1**: All components expose `health_check()` method
- [ ] **AC4.2**: Core calls `health_check()` on all components periodically
- [ ] **AC4.3**: Core updates component state based on health check results
- [ ] **Evidence**: Add test that verifies health checks are called and state is updated

### 5.5 Failure Handling
- [ ] **AC5.1**: Core catches exceptions from component execution
- [ ] **AC5.2**: Core handles failures per `contracts/failure-semantics.md`:
  - Component crash → Mark as FAILED, emit crash event
  - Dependency unavailable → Mark as DEGRADED or FAILED, emit dependency failure event
  - Resource exhaustion → Mark as DEGRADED, emit resource exhaustion event
- [ ] **AC5.3**: Core shuts down system on unrecoverable conditions (per failure semantics)
- [ ] **Evidence**: Add test that verifies failure handling for each failure type

### 5.6 Graceful Shutdown
- [ ] **AC6.1**: Core calls `stop()` on all components during shutdown
- [ ] **AC6.2**: Components transition RUNNING → STOPPING → STOPPED states
- [ ] **AC6.3**: Core waits for components to stop before exiting
- [ ] **Evidence**: Add test that verifies graceful shutdown sequence

### 5.7 Production Readiness
- [ ] **AC7.1**: System can be installed at customer site without manual intervention
- [ ] **AC7.2**: System starts all components automatically on boot (via systemd)
- [ ] **AC7.3**: System detects and logs component failures
- [ ] **AC7.4**: System shuts down cleanly on SIGTERM/SIGINT
- [ ] **Evidence**: Manual installation and operation test at customer site

### 5.8 Installer Alignment
- [ ] **AC8.1**: Installer does not start components as separate processes
- [ ] **AC8.2**: Installer only starts Core process (Core starts all components)
- [ ] **AC8.3**: Systemd service file tracks only Core process
- [ ] **Evidence**: Verify installer script and systemd service file

---

## 6. Implementation Priority

### Priority 1: Critical (Ship-Blocker)
1. **Component Execution** (Gap 1)
   - Without this, system does not function
   - Estimated effort: 2-3 days

2. **Dependency Ordering** (Gap 2)
   - Required for correct startup sequence
   - Estimated effort: 1 day

3. **Supervision Loop** (Gap 3)
   - Required for failure detection
   - Estimated effort: 2-3 days

### Priority 2: High (Production Risk)
4. **Health Checking** (Gap 4)
   - Required for operational visibility
   - Estimated effort: 1-2 days

5. **Failure Handling** (Gap 5)
   - Required for failure semantics compliance
   - Estimated effort: 2 days

### Priority 3: Medium (Operational Improvement)
6. **Component State Tracking** (Gap 6)
   - Improves observability
   - Estimated effort: 1 day

**Total Estimated Effort**: 9-12 days

---

## 7. Risk Assessment

### Risk 1: Component Threading Model
- **Risk**: FastAPI services (Ingest, UI) use uvicorn which expects to run in main thread
- **Mitigation**: Run uvicorn in background thread, ensure proper signal handling
- **Impact**: Medium - May require uvicorn configuration changes

### Risk 2: Component Shutdown Coordination
- **Risk**: Components may not respond to shutdown signals promptly
- **Mitigation**: Implement timeout-based shutdown with force-kill fallback
- **Impact**: Medium - May require component modifications

### Risk 3: Health Check Implementation
- **Risk**: Batch components (Correlation, AI Core, Policy) don't have health endpoints
- **Mitigation**: Implement health check functions that verify processing loop is running
- **Impact**: Low - Straightforward implementation

### Risk 4: Failure Semantics Compliance
- **Risk**: Failure handling may not match `contracts/failure-semantics.md` exactly
- **Mitigation**: Review failure semantics contract and implement exactly as specified
- **Impact**: Medium - Requires careful implementation

---

## 8. Conclusion

Core Runtime is **NOT** a real orchestrator. It loads modules but never executes them. The system cannot function in production without manual intervention. This is a **SHIP-BLOCKER**.

**Required Actions**:
1. Implement component execution with standard interface
2. Implement dependency ordering and enforcement
3. Implement supervision loop with health monitoring
4. Implement failure handling per failure semantics contract
5. Remove installer workaround
6. Verify all acceptance criteria are met

**Estimated Time to Fix**: 9-12 days

**Recommendation**: Do not ship until Phase-10 is complete and all acceptance criteria are met.

---

**End of Report**
