# Performance narrative (~3 minutes)

*Target ~420 spoken words at ~140 wpm.*

---

Tonight we ran one Mun-orbit evaluation with two models inside the same harness: planning tools, file tools, and a scientific loop—hypothesize, instrument, fly, read telemetry, post-mortem, iterate.

The task sounds easy: Kerbal Space Program, kRPC Python, operator builds the manifest. Success is a stable Mun orbit. In practice it tests whether an agent closes the loop on reality or only writes convincing plans.

**DeepSeek**, once we forced self-instrumentation, was disciplined. Five attempts: hypotheses, manifests, structured telemetry every five seconds. Final attempt: Skipper stack to roughly a hundred fifty kilometres apoapsis—honestly farther along the mission timeline than most “AI plays Kerbal” demos ever document. Failure was specific and measurable: throttle inherited after staging, tens of seconds of unwanted coast burn, then a script sanity cap that rejected a normal nine-hundred-metres-per-second circularization. Its own post-mortem named each mechanism. That is scientific behaviour even without Mun orbit.

**GPT session one** chose different hardware—SRBs, twin Swivel cores—and hit integration failure: after booster drop the craft showed throttle but no sustained liquid thrust. Telemetry nailed it—fuel read full while nothing burned because propellant sat in tanks no longer feeding an active engine. Reasoning held; the design allowed the operator to mis-wire staging.

**GPT session two** used Making History parts and clearer manifests. The bug moved again: staging keyed on **total vessel** fuel, so when the first core went dry but upper tanks stayed full, “stage now” never triggered. Same lesson—sensing and staging kill you before napkin delta‑v does.

**Systems note:** completion tokens per turn were not the bottleneck. **Context** was—every giant `read_file` stayed in history until things crashed. We trimmed skills, moved methodology files on-demand, and told the model not to re-load every old telemetry dump each turn.

Headline: nobody Mun tonight. The win is **evidence**: falsifiable post-mortems tied to numbers on disk. DeepSeek flew highest; GPT mapped different failure modes. Same eval, same harness—different bugs. That is what an agent eval should look like.

If you take one lesson into the next build: **instrument before you argue.** When altitude, fuel, and stage disagree with the narrative in your head, the log wins—and both models eventually agreed with theirs.

---

*End.*
