
================================================================================
METHOD OF PROCEDURE (MOP) - aBotTesty Enhancement
Project: Adaptive, Persistent, Creative Navigation Learning
Version: 1.0
Date: 2026-05-08
================================================================================

OBJECTIVE:
Enhance aBotTesty autonomous TV navigation bot to be more adaptive (UI pattern 
recognition), more persistent (unreachable state tracking), and more creative 
(action sequence learning), while maintaining safety protocols and verification 
at every phase.

EXPECTED OUTCOMES:
- 30-40% improvement in exploration efficiency
- 50%+ improvement in path discovery completeness  
- Zero safety regressions
- All existing tests continue passing

================================================================================
## 1. PREREQUISITES
================================================================================

**Technical Prerequisites:**
- Python 3.10+ with existing aBotTesty dependencies (cv2, numpy)
- Access to /tmp/dish_chat_agent/aBotTesty_analysis/repo/
- Write access to auto_crawler.py and focus_detector.py
- Test STB simulator or synthetic test environment

**Knowledge Prerequisites:**
- Understanding of existing FeatureExtractor, NavigationGraph, CrawlerBrain
- Familiarity with state fingerprinting and similarity scoring
- Understanding of reward/punishment protocol

**Approval Prerequisites:**
- Code changes to be tested synthetically before STB hardware testing
- Each phase independently deployable
- Safety checks maintained throughout

**Environmental Prerequisites:**
- Development workspace: /tmp/dish_chat_agent/aBotTesty_analysis/
- Test data directory: /tmp/dish_chat_agent/aBotTesty_analysis/test_data/
- Backup of original code before modifications

================================================================================
## 2. PROCEDURE
================================================================================

### PHASE A: UI Pattern Recognition (Steps 1-7)
**Goal: Make crawler adaptive to different UI types**

**Step A1: Create UIPattern enum and PatternRecognizer class**
- Add UIPattern enum (GRID_MENU, LINEAR_MENU, FORM, VIDEO_PLAYER, INFO_CARD)
- Implement PatternRecognizer with classification methods
- Test: Verify each pattern type correctly identified on sample screenshots
- Success: 5 different UI types classified with >80% confidence

**Step A2: Add pattern detection to FeatureExtractor**
- Extract layout hints from focus movements
- Add grid/linear detection based on focus history
- Test: Feed 10 sample states, verify pattern classification
- Success: Patterns match manual visual inspection

**Step A3: Integrate pattern-aware state fingerprinting**
- Store detected pattern in ScreenFingerprint
- Update NavigationGraph to track state patterns
- Test: Create states, verify patterns persisted to nav_graph.json
- Success: Patterns saved and loaded correctly

**Step A4: Implement adaptive action selection**
- Add _prefer_directional(), _prefer_select_and_back(), _prefer_meta_buttons()
- Bias action ordering based on detected pattern
- Test: Synthetic crawler with known patterns, verify action preference
- Success: Grid menus prioritize arrows, forms avoid arrow spam

**Step A5: Add adaptive similarity thresholds**
- Implement AdaptiveThresholdModel class
- Per-pattern threshold configuration (grid=0.82, video=0.75, menu=0.94)
- Test: States with different patterns get different thresholds
- Success: Video content less sensitive, static menus more strict

**Step A6: Integration test**
- Run full synthetic crawler with mixed UI types
- Verify adaptive behavior throughout exploration
- Test: 50-step crawl with grid, form, video, menu transitions
- Success: Fewer duplicate states, faster exploration

**Step A7: Verification checkpoint**
- All existing tests still pass
- New tests cover pattern recognition
- No safety regressions
- Document pattern classification accuracy

### PHASE B: Action Sequence Learning (Steps 8-13)
**Goal: Make crawler creative with compound actions**

**Step B1: Create SequenceLearner class**
- Implement action history tracking (deque, maxlen=1000)
- Add LearnedSequence dataclass
- Test: Record 100 actions, verify history maintained
- Success: Action history persisted correctly

**Step B2: Implement n-gram sequence mining**
- Add mine_sequences() method (lengths 2-5)
- Count occurrences with collections.Counter
- Test: Feed sequence [A,B,C,A,B,C,A,B,D], verify AB and ABC detected
- Success: Frequent sequences identified with occurrence counts

**Step B3: Add reward-based sequence filtering**
- Compute average reward for each sequence
- Keep only sequences with avg_reward > 2.0
- Test: Mine from history with known rewards, verify filtering
- Success: High-reward sequences retained, low-reward discarded

**Step B4: Implement sequence suggestion**
- Add suggest_next_action() method
- Match recent actions to sequence prefixes
- Test: Recent=[A,B], learned=[A,B,C], verify C suggested
- Success: Correct completions suggested

**Step B5: Integrate into action selection**
- Update choose_next_action() to check sequences first
- Fall back to reward-based ordering if no sequence match
- Test: Crawler with learned sequence, verify completion triggered
- Success: Sequences executed when pattern detected

**Step B6: Add sequence learning to exploration loop**
- Record actions in try_action()
- Periodically mine new sequences (every 50 steps)
- Test: 200-step crawl, verify sequences discovered and used
- Success: Useful sequences learned and applied

**Step B7: Verification checkpoint**
- Existing tests pass
- Sequence learning tests pass
- Check learned_sequences.json persistence
- Verify no infinite loops from bad sequences

### PHASE C: Unreachable State Tracking (Steps 14-19)
**Goal: Make crawler persistent with difficult states**

**Step C1: Create PersistenceTracker class**
- Implement UnreachableState dataclass
- Add unreachable state storage and persistence
- Test: Mark state unreachable, verify saved to JSON
- Success: Unreachable states persisted across restarts

**Step C2: Track navigation failures**
- Update navigate_to_state() to record failures
- Store failed routes and attempt counts
- Test: Navigation failure, verify recorded with route
- Success: Failed attempts tracked with context

**Step C3: Implement priority scoring**
- Boost priority for important-looking states (settings, parental, admin)
- Sort unreachable states by priority
- Test: Mix of states, verify priority ordering
- Success: Important states ranked higher

**Step C4: Add retry candidate selection**
- Implement get_retry_candidates() with max_attempts filter
- Return priority-sorted list
- Test: Request retry candidates, verify correct subset
- Success: High-priority, low-attempt states returned

**Step C5: Integrate into continuous exploration**
- After frontier exhausted, try unreachable states
- Attempt alternative routes
- Test: Crawler exhausts frontier, verify retry attempts
- Success: Previously unreachable states retried

**Step C6: Add success tracking**
- Mark states reachable when navigation succeeds
- Remove from unreachable list
- Test: Retry succeeds, verify removed from tracking
- Success: State removed after successful reach

**Step C7: Verification checkpoint**
- Existing tests pass
- Persistence tracking tests pass
- Verify unreachable_states.json format
- Check retry logic doesn't cause infinite loops

### PHASE D: Integration Testing (Steps 20-23)

**Step D1: Combined feature test**
- Enable all three enhancements
- Run 300-step synthetic crawl
- Test: Pattern recognition + sequences + persistence all active
- Success: All features work together, no conflicts

**Step D2: Performance validation**
- Measure exploration efficiency (states per step)
- Compare to baseline (original code)
- Test: Baseline vs enhanced on same synthetic UI
- Success: 30%+ efficiency improvement

**Step D3: Safety validation**
- Verify dangerous text blocking still works
- Check action attempt limits respected
- Test: Risky screens, verify SELECT blocked
- Success: All safety mechanisms intact

**Step D4: Documentation and delivery**
- Update README with new features
- Document configuration options
- Create example usage guide
- Success: Complete documentation package

================================================================================
## 3. VERIFICATION STEPS
================================================================================

**After Each Step:**
- Unit test for new functionality passes
- No existing tests broken
- Code committed with descriptive message
- Manual inspection confirms expected behavior

**After Each Phase:**
- All phase tests pass
- Integration with existing code verified
- Performance impact measured
- Safety checks confirmed

**Phase A Success Criteria:**
- 5 UI patterns correctly identified (>80% accuracy)
- Adaptive thresholds reduce duplicate states by 20%+
- Pattern-appropriate action selection demonstrated
- Zero safety regressions

**Phase B Success Criteria:**
- Useful sequences discovered (min 5 sequences, avg reward >2.0)
- Sequences applied during exploration
- learned_sequences.json populated correctly
- No infinite loops from sequence execution

**Phase C Success Criteria:**
- Unreachable states tracked and retried
- Priority ordering works correctly
- Previously unreachable states reached after retry
- unreachable_states.json maintained correctly

**Phase D Success Criteria:**
- Combined efficiency gain 30%+ vs baseline
- Path discovery completeness 50%+ improvement
- All existing tests pass
- Safety mechanisms intact

================================================================================
## 4. ROLLBACK PROCEDURE
================================================================================

**Rollback Triggers:**
- Existing tests failing
- Safety mechanism bypassed
- Infinite loops detected
- Performance degradation >10%

**Rollback Steps:**

**Level 1 - Feature Rollback:**
```bash
# Revert specific feature file
git checkout HEAD~1 -- auto_crawler.py
# Or revert specific commit
git revert <commit-hash>
```

**Level 2 - Phase Rollback:**
```bash
# Revert entire phase (multiple commits)
git revert <phase-start-commit>..<phase-end-commit>
```

**Level 3 - Full Rollback:**
```bash
# Restore from backup
cp /tmp/dish_chat_agent/aBotTesty_analysis/backup/auto_crawler.py \
   /tmp/dish_chat_agent/aBotTesty_analysis/repo/auto_crawler.py
```

**Post-Rollback Verification:**
- All original tests pass
- Baseline behavior restored
- No residual state from failed feature

================================================================================
## 5. SUCCESS CRITERIA (FINAL)
================================================================================

**Quantitative Metrics:**
1. Exploration efficiency: 30-40% fewer steps to discover 80% of states
2. Path completeness: 50%+ more states/edges discovered in fixed step budget
3. Duplicate state reduction: 20%+ fewer false-positive state matches
4. Sequence discovery: 5+ useful sequences learned per 200-step run
5. Persistence success: 30%+ of previously unreachable states reached on retry

**Qualitative Metrics:**
1. Pattern recognition: Manual review confirms correct UI type classification
2. Safety preservation: Zero regressions in dangerous action blocking
3. Code quality: Peer review approves architecture and implementation
4. Documentation: Complete usage guide and API documentation

**Definition of Done:**
- All phases (A, B, C, D) completed
- All verification checkpoints passed
- Performance improvements demonstrated
- Safety mechanisms verified intact
- Documentation complete
- No rollback required (or rolled back issue resolved and redeployed)

================================================================================
## 6. EXECUTION LOG
================================================================================

Phase | Step | Status | Date | Notes
------|------|--------|------|-------
A     | A1   | READY  | -    | UI pattern recognition
A     | A2   | READY  | -    | Pattern detection
A     | A3   | READY  | -    | Pattern persistence
A     | A4   | READY  | -    | Adaptive action selection
A     | A5   | READY  | -    | Adaptive thresholds
A     | A6   | READY  | -    | Integration test
A     | A7   | READY  | -    | Verification checkpoint
B     | B1   | READY  | -    | SequenceLearner class
B     | B2   | READY  | -    | N-gram mining
B     | B3   | READY  | -    | Reward filtering
B     | B4   | READY  | -    | Sequence suggestion
B     | B5   | READY  | -    | Integration
B     | B6   | READY  | -    | Learning loop
B     | B7   | READY  | -    | Verification checkpoint
C     | C1   | READY  | -    | PersistenceTracker class
C     | C2   | READY  | -    | Failure tracking
C     | C3   | READY  | -    | Priority scoring
C     | C4   | READY  | -    | Retry candidates
C     | C5   | READY  | -    | Integration
C     | C6   | READY  | -    | Success tracking
C     | C7   | READY  | -    | Verification checkpoint
D     | D1   | READY  | -    | Combined test
D     | D2   | READY  | -    | Performance validation
D     | D3   | READY  | -    | Safety validation
D     | D4   | READY  | -    | Documentation

================================================================================
END OF MOP
================================================================================
