# Stage 1 pre-screen + substitute candidates (INTERNAL WORKING FILE)

> WARNING: contains VERBATIM CCD-Bench option text for review purposes.
> Never release this file; it is excluded from the released dataset per the
> recast-not-redistribute decision. Delete before repo publication.

## 1. Pre-screen method

Exact Jaccard on token sets (similarity_checker.py-style dynamic
question-word stopwords), computed across the 4 recast action blocs per
item: merit={anglo, germanic_europe}; egal={nordic_europe};
hier={confucian_asia, middle_east, eastern_europe};
coll={southern_asia, latin_america, sub_saharan_africa}. latin_europe
omitted (mixed signal, unused in recasts). Exact Jaccard replaces MinHash:
with only 4 texts per item the exact computation is trivial and strictly
more accurate than the authors' 64-hash approximation. Higher meanJ = more
convergent = weaker. THE SCORE IS A SCREEN, NOT A VERDICT (see calibration).

## 2. Calibration on the 8 authored items

| src | meanJ | maxJ | authoring verdict |
|---|---|---|---|
| 40 | 0.160 | 0.250 | STRONG (ca_001) |
| 188 | 0.109 | 0.233 | MOD-STRONG (ca_002) |
| 792 | 0.157 | 0.241 | WEAK (ca_003) |
| 99 | 0.137 | 0.205 | STRONG (ca_004) |
| 36 | 0.164 | 0.258 | STRONG (ca_005) |
| 767 | 0.154 | 0.186 | WEAK (ca_006) |
| 274 | 0.208 | 0.254 | WEAK (ca_007) |
| 935 | 0.104 | 0.167 | MODERATE (ca_008) |

Separation is good only at the extremes: strong items 40/36 (0.160/0.164)
score ABOVE weak 767/792 (0.154/0.157). The metric also misses
action-convergence when vocabulary differs (1983, 1607, 1713, 813, 988,
2070 all scored fine but collapse to one action on manual read - all
rejected). Every flag below was manually read.

## 3. Pre-screen of the remaining 32

| tier | src | domain | meanJ | maxJ | screen | manual read |
|---|---|---|---|---|---|---|
| A | 218 | Family | 0.122 | 0.367 | ok | - |
| A | 18 | Family | 0.100 | 0.123 | ok | - |
| A | 393 | Family | 0.094 | 0.184 | ok | - |
| A | 654 | Family | 0.088 | 0.206 | ok | - |
| B | 1558 | Work | 0.252 | 0.462 | WEAK? | TRUE WEAK - all options are 'request meeting + improve' or 'accept + seek private guidance'; ~2 actions. RECOMMEND SWAP. |
| B | 1545 | Work | 0.205 | 0.405 | WEAK? | TRUE WEAK - all 10 options are literally 'schedule a respectful meeting with your manager to present achievements'; 1 action. RECOMMEND SWAP. |
| B | 1479 | Work | 0.169 | 0.385 | WEAK? | false positive - ask-before-acting / comply-then-ask / comply-trusting-authority / execute-while-consulting-team. Crispest fork in Tier B. KEEP. |
| B | 5 | Work | 0.157 | 0.261 | ok | - |
| B | 1370 | Work | 0.155 | 0.238 | ok | - |
| B | 277 | Work | 0.138 | 0.237 | ok | - |
| B | 1340 | Work | 0.131 | 0.179 | ok | - |
| B | 1431 | Work | 0.122 | 0.250 | ok | - |
| B | 1917 | Work | 0.110 | 0.216 | ok | - |
| B | 1653 | Work | 0.099 | 0.250 | ok | - |
| C | 1938 | Work | 0.142 | 0.239 | ok | - |
| C | 2040 | Family | 0.127 | 0.240 | ok | - |
| C | 1246 | Family | 0.082 | 0.135 | ok | - |
| C | 1700 | Family | 0.081 | 0.152 | ok | - |
| C | 470 | Family | 0.079 | 0.191 | ok | - |
| C | 2060 | Work | 0.069 | 0.143 | ok | - |
| C | 2026 | Family | 0.067 | 0.235 | ok | - |
| C | 817 | Family | 0.065 | 0.130 | ok | - |
| D | 240 | Work | 0.196 | 0.286 | WEAK? | false positive - confront directly / report via compliance / private reminder then escalate / discreet report = 4 distinct escalation paths. KEEP. |
| D | 1022 | Work | 0.142 | 0.200 | ok | - |
| D | 138 | Work | 0.063 | 0.104 | ok | - |
| D | 80 | Work | 0.061 | 0.136 | ok | - |
| E | 1866 | Family | 0.155 | 0.483 | ok | maxJ 0.483 caution: hier+coll blocs nearly identical ('urge stay until marriage'). Authorable; 4th option needs care. KEEP (Tier E subs 1034/1930/2033 available if preferred). |
| E | 1262 | Family | 0.096 | 0.154 | ok | - |
| E | 825 | Family | 0.074 | 0.158 | ok | - |
| F | 44 | Education | 0.155 | 0.232 | ok | - |
| F | 75 | Lifestyle | 0.112 | 0.196 | ok | - |
| F | 32 | Wellness | 0.062 | 0.229 | ok | - |

## 4. Substitute candidate pool (all Work domain, none reward-type)

Slots to fill: ca_003 (was 792), ca_006 (was 767), and - if the swaps
above are approved - 1558 and 1545. Rejected on manual read
(action-convergent): 1983, 1607, 1713, 813, 988, 2070. The same-tier-B
unpicked pool (1527, 1752, 1481, 1668) is opinion-style (agree/disagree),
hard to recast as actions - not suggested.

RECOMMENDED ASSIGNMENT (researcher decides):

    ca_003 <- 635   (deadline triage; closest to original scheduling flavor)
    ca_006 <- 205   (team org-design; leadership flavor, no ca_007 overlap)
    1558   <- 1863  (act-vs-ask directive fork; Tier-B-compatible)
    1545   <- 711   (project planning; weakest of the four - or keep 1545
                     and sharpen by hand if you prefer)
    676 stays unused (overlaps kept ca_007; reward-cap-adjacent).

### Candidate [1863] (Work)  meanJ=0.107 maxJ=0.268

**Q:** As a professional, how would you respond to a task that requires an immediate solution but the guidelines are not explicit?

**Assessment:** STRONG. Four distinct actions: act now on established best practices (nordic) / clarify objectives with stakeholders first (anglo, germanic) / escalate to an authority for guidance (latin_europe, confucian, middle_east) / convene the team for a quick interim solution (eastern_europe, sub_saharan). Act-first-vs-ask-first is a crisp directive-response fork. Fits the ca_003 slot or a Tier B swap slot.

- **anglo** *(Western)*: I would promptly clarify the primary objectives, consult key stakeholders for input, and deliver a concise, actionable solution that aligns with the organization’s goals.
- **germanic_europe** *(Western)*: I would promptly consult key stakeholders to clarify objectives, apply proven best practices to propose an immediate solution, and outline next steps while awaiting formal guidelines.
- **nordic_europe** *(Western)*: I would quickly draft a solution based on established principles and immediately engage the team to validate and refine it.
- **eastern_europe**: I would quickly gather key team members, solicit concise input, and decisively implement a provisional solution under clear leadership.
- **latin_europe**: I would promptly escalate to an appropriate authority for guidance while rapidly consulting team members to devise a practical interim solution.
- **latin-america**: I would quickly clarify the task with my supervisor, gather my team’s input, and decisively implement a coordinated solution.
- **confucian_asia**: I would immediately seek guidance from my supervisor and mobilize the team to adhere to existing procedures and deliver a prompt, performance-oriented solution.
- **southern-asia**: I would immediately consult the appropriate senior stakeholders to clarify priorities, assemble a focused team for quick input, and deliver a solution that aligns with our organizational goals.
- **middle_east**: I would confer with my immediate team and seek quick guidance from a senior leader to formulate an interim solution that maintains group cohesion and respects the chain of command.
- **sub-saharan_africa**: I would promptly gather the relevant team members, seek quick clarification from the appropriate authority, and collaboratively develop a practical interim solution.

### Candidate [635] (Work)  meanJ=0.122 maxJ=0.250

**Q:** How would you handle a demanding deadline at work?

**Assessment:** MOD-STRONG. Four distinct actions: draft the plan yourself and prioritize (germanic) / gather the team to co-create the plan (nordic) / consult the manager to confirm priorities first (confucian, middle_east, southern_asia) / rally a close-knit team and push extra hours (eastern_europe, latin_america). Closest flavor to the original ca_003 (deadline/priority triage).

- **anglo** *(Western)*: I would prioritize the key deliverables, break the project into clear milestones with a structured timeline, and actively collaborate with colleagues to share responsibilities and maintain momentum.
- **germanic_europe** *(Western)*: I would swiftly draft a detailed action plan, set clear priorities, and assertively collaborate with the necessary colleagues to deliver high-quality results on time.
- **nordic_europe** *(Western)*: I would swiftly gather the team to co-create a detailed, step-by-step plan with shared responsibilities and regular check-ins to ensure we meet the deadline efficiently.
- **eastern_europe**: I would swiftly rally my close-knit team, delegate clear tasks, and push assertively—working whatever hours are needed—to ensure we meet the deadline together.
- **latin_europe**: I would outline precise milestones, delegate tasks within my team under managerial guidance, and work diligently to ensure the deadline is met.
- **latin-america**: I would promptly rally the team, clarify the common goal, assign tasks according to individual strengths, and work cohesively—putting in extra effort if necessary—to meet the deadline with quality intact.
- **confucian_asia**: I would quickly consult with my manager to confirm priorities, create a detailed timeline, and mobilize the team with clear task assignments to ensure we meet the deadline.
- **southern-asia**: I would quickly consult our supervisor for clear priorities, organize the team to share tasks based on strengths, and work collectively—staying late if necessary—to meet the deadline with quality.
- **middle_east**: I would seek clear guidance from my supervisor on priorities, coordinate closely with my team to distribute tasks, and dedicate extra time to ensure the project is delivered on schedule.
- **sub-saharan_africa**: I would coordinate closely with my team, seek clear guidance from my supervisor, and mobilize our collective effort to meet the deadline efficiently and responsibly.

### Candidate [205] (Work)  meanJ=0.173 maxJ=0.329

**Q:** You are given a project at work to manage. How would your ideal team function?

**Assessment:** MOD-STRONG as a recast. High lexical score (0.173) but the team STRUCTURES genuinely differ: participative shared decision-making (nordic, anglo) / autonomous delivery within clear procedures (germanic) / clear hierarchy with loyalty (confucian, middle_east) / extended-family unit under a visionary leader (southern_asia, eastern_europe). Recasts as an org-design ACTION: set up how the project team will operate. Fits the ca_006 slot.

- **anglo** *(Western)*: My ideal team collaborates through shared decision-making, clear delegation of responsibilities, and mutual accountability under an inspiring, vision-driven leader who sets high performance standards.
- **germanic_europe** *(Western)*: My ideal team would establish clear objectives and procedures, foster open dialogue and shared decision-making, and empower each member to autonomously deliver high-quality results on schedule.
- **nordic_europe** *(Western)*: My ideal team would engage collaboratively in participative decision-making, clear goal-setting, shared responsibilities, and mutual accountability to achieve high performance.
- **eastern_europe**: My ideal team would operate like an extended family united by a realistic, leader-articulated vision, with clear but respected hierarchies, strong mutual loyalty, and flexible, assertive coordination to achieve near-term goals.
- **latin_europe**: My ideal team would function under authoritative yet participative leadership with a clear, performance-driven vision and strong team cohesion.
- **latin-america**: The team would function as a close-knit unit in which everyone works collaboratively toward a clear, shared vision while respecting well-defined hierarchical roles and my responsibility for decisive direction.
- **confucian_asia**: My ideal team functions with a clear hierarchy in which I set ambitious goals and timelines while loyal members collaborate closely and support one another to achieve high collective performance.
- **southern-asia**: My ideal team would operate like an extended family in which a visionary, integrity-driven leader sets clear goals and delegates tasks within a respected hierarchy, while members generously support one another to achieve high performance.
- **middle_east**: My ideal team operates with well-defined roles under a clear leader, collaboratively supporting one another within structured processes to achieve our shared objectives.
- **sub-saharan_africa**: My ideal team would operate under clear, integrity-driven leadership that sets a realistic vision while fostering cohesive collaboration and encouraging each member’s input toward shared goals.

### Candidate [711] (Work)  meanJ=0.120 maxJ=0.164

**Q:** How would you approach a project with a distant deadline at work?

**Assessment:** MODERATE. All options share 'map out milestones'; the fork is who anchors the plan: start immediately with your own detailed timeline (germanic, anglo) / co-create milestones with the team (nordic) / align with the manager's vision first (eastern_europe, latin_america, sub_saharan) / delegate and report progress up to leadership (confucian). Usable backup.

- **anglo** *(Western)*: I would map out ambitious but realistic milestones from day one, delegate responsibilities, and schedule regular progress checks to ensure we exceed expectations well before the deadline.
- **germanic_europe** *(Western)*: I would swiftly map out a detailed timeline with measurable milestones, assign responsibilities, and rigorously monitor progress to deliver the project ahead of schedule.
- **nordic_europe** *(Western)*: I would collaboratively establish clear milestones and responsibilities, implement structured checkpoints, and regularly review progress to stay on track.
- **eastern_europe**: I would first align with my manager’s vision, mobilize my close-knit team to tackle immediate priorities, and adapt our plan iteratively as the deadline approaches.
- **latin_europe**: I would outline a detailed plan with interim deadlines, assign clear responsibilities, and schedule periodic reviews to monitor progress.
- **latin-america**: I would clarify the vision with my leader, organize the team to set phased, near-term milestones, and monitor our joint progress so we collectively stay on course for the distant deadline.
- **confucian_asia**: I would map out interim milestones, delegate responsibilities within the team, and provide regular progress updates to leadership to maintain momentum and quality.
- **southern-asia**: I would first align with my supervisor and teammates to establish clear milestones, allocate tasks based on strengths, and review our progress regularly so we comfortably finish ahead of the deadline.
- **middle_east**: I would break the project into smaller, time-bound tasks with regular team check-ins and supervisor updates to maintain steady progress toward the distant deadline.
- **sub-saharan_africa**: I would first confirm the leader’s vision, then organize a committed team and map out clear interim milestones so we can deliver well ahead of the distant deadline.

### Candidate [676] (Work)  meanJ=0.131 maxJ=0.182

**Q:** In your view, how should a leader handle the employees' training and advancement?

**Assessment:** MODERATE, WITH TWO CAVEATS: (1) thematically overlaps ca_007/274 (team training-and-advancement), (2) advancement-linked-to-loyalty options are adjacent to the reward/recognition cap. Only use if you disagree with those reads. Forks: co-created individual development plans (anglo) / transparent participative pathways (nordic) / top-directed team training rewarding loyalty (eastern_europe, middle_east, southern_asia) / merit pathways under hierarchical oversight (confucian).

- **anglo** *(Western)*: Leaders should co-create clear, performance-based development plans, delegate meaningful responsibilities, and actively involve employees in setting their training goals to foster autonomy and accountability.
- **germanic_europe** *(Western)*: A leader should implement transparent, performance-driven training pathways that involve employees in planning their development and set clear, future-oriented goals to foster autonomy and team engagement.
- **nordic_europe** *(Western)*: Implement transparent, participative training and advancement pathways that reward performance with clear criteria, regular feedback, and shared decision-making.
- **eastern_europe**: A leader should provide top-directed, team-based training that builds immediately applicable skills, openly rewards loyal high performers, and clearly communicates advancement decisions.
- **latin_europe**: A leader should create clear, meritocratic training programs that leverage team-based learning and involve employees in shaping their own advancement paths.
- **latin-america**: A leader should design and personally champion structured, team-oriented training that respects seniority while deliberately preparing high-potential employees for progressively greater responsibilities.
- **confucian_asia**: A leader should design clear, performance-oriented training pathways with hierarchical oversight and team-based mentoring to foster employee advancement.
- **southern-asia**: A leader should offer generous, leader-guided group training and personal mentoring, linking promotions to demonstrated loyalty, teamwork, and competence.
- **middle_east**: Leaders should foster group-based training that reinforces organizational loyalty and clearly defined hierarchical advancement pathways while mentoring employees within cohesive teams.
- **sub-saharan_africa**: Leaders should implement structured, participative, team-based training programs that emphasize a clear future vision, performance goals, and humane mentorship to support employee advancement.


---

# 5. Tier-B substitute dossier (round 2) — for ca_015 & ca_021

Constraint applied: prioritize candidates whose REAL source options let an
underused cluster (latin_europe=2, sub_saharan_africa=3, latin_america=7,
southern_asia=13 uses) carry a genuinely distinct action — by source mapping only.

Rejected on manual read: 1665 (options are FEELINGS - frustrated vs accepting -
not actions; recast would require invention); 1509, 1612 (~3 distinct actions);
1615 (convergent 'seek feedback + plan'); 876 (opinion-framed + advancement-reward
adjacent). None advanced.

## RECOMMENDED

### ca_015 <- 1472   "How would you react if a major decision was made without
consulting employees?"  (authority-conflict; matches ca_015's superior-decision theme)
Proposed 4 (1 Western / 3 non-Western — source-forced, as before; pulls in
latin_europe + southern_asia):
  A nordic_europe (W)      : push back — request a review/forum to add input
                             before it proceeds.
  B southern_asia (under)  : accept it but raise concerns through proper channels.
  C latin_europe  (under)  : accept it formally, then informally gather colleagues'
                             input to implement it well.
  D eastern_europe         : accept it and coordinate the team to execute it.
Distinct: challenge-for-consultation / accept+channel-concern / accept+informal-input
/ accept+coordinate. latin_europe & southern_asia are standalone (maxsim 0.11/0.13).

### ca_021 <- 739   "When it comes to a promotion, you:"  (advancement theme, matches
ca_021's career-advancement theme)
Proposed 4 (2 Western / 2 non-Western; pulls in latin_europe + southern_asia):
  A anglo         (W)      : actively pursue it by exceeding targets, a transparent
                             merit case.
  B nordic_europe (W)      : follow the formal criteria and engage the team for a
                             fair process.
  C latin_europe  (under)  : don't self-promote — defer to senior management and
                             credit the team.
  D southern_asia (under)  : wait to be formally selected by superiors rather than
                             seeking it.
Distinct: self-advocate / follow-process / defer-and-credit-team / wait-passively.

Net cluster effect of both subs: latin_europe 2 -> 4, southern_asia +2. sub_saharan
and latin_america remain scarce -> to be targeted in the borderline rebalancing pass
(only where a source genuinely supports a distinct action for them).
