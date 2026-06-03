# Transcript: "Gemini Enterprise Agent Platform" by Holt Skinner (Google Cloud DevRel)

**Source:** https://youtu.be/j8qW5poBkEU
**Speaker:** Holt Skinner, Developer Advocate, Google Cloud AI
**Pulled:** 2026-06-02 via youtube-transcript-yt-dlp skill (auto-captions)
**Why this file exists:** Canonical mid-2026 Google source on every component of the Agent Platform. The 02b-gemini-enterprise-agent-platform.md synthesis file is derived from this transcript.

---

[0.38s] HOLT SKINNER: Hi there.
[1.34s] My name is Holt Skinner, and I'm a developer advocate for Google Cloud AI.
[5.16s] Google Cloud just announced Gemini Enterprise Agent Platform, which includes everything developers need for creating enterprise grade, scalable, and secure agents.
[14.28s] So let's break down all the key parts and how they fit into the development lifecycle for AI agents.
[19.88s] Agent Platform's features are focused around four key parts of the agent development lifecycle — build, scale, govern, and optimize.
[28.05s] Everything that is mentioned in this video has tutorials and documentation in the GitHub repository also linked in the description, so be sure to check them out afterwards and try everything out for yourself.

[39.12s] Before we start, a quick note on the name.
[41.56s] If you've been building with Vertex AI, you're in the right place.
[45.04s] Agent Platform is an evolution of Vertex AI, including Model Garden and Model Training, that is now restructured as an agent-first ecosystem.
[52.68s] So you'll see some mixed terminology as we transition, but please be assured that the core Vertex AI functionality remains unchanged.

[67.36s] First, if we want to build an agent, we — either a human or an agent — need to write some code.
[73.72s] Google uses Agent Development Kit, or ADK, as the framework to build agents.
[76.88s] It currently supports four languages — Python, TypeScript, Java, and Go.
[84.36s] ADK is a comprehensive framework for building various types of agents, ranging from simple sequential agents to complex multi-agent systems.
[92.42s] And in the latest version, you can build deterministic graph-based agents, so you can choose between fully dynamic model-led reasoning or more strict deterministic logic.
[102.44s] While optimized for Gemini, ADK provides integration with any model, including Claude from Anthropic or open-weight models from Ollama.
[110.48s] This flexibility lets you mix and match models to meet the needs of your agent tasks, whether strictly text based or using a mix of multi-modal data.

[119.72s] When you're designing your agent, you'll want to connect to external tools.
[123.39s] The standard pattern is to use Model Context Protocol, MCP, which is fully supported by ADK.
[129.47s] And if you want to connect to external agents, ADK has built-in support for agent-to-agent protocol.
[135.39s] You can collaborate with any agent, no matter what framework it was created in or where it's running.
[140.55s] Multi-agent systems can be built like microservices, and A2A describes the API surface, so every remote agent supports the same data structures and methods.
[149.31s] Most agent frameworks, like LangGraph, CrewAI, and AG2, have built-in support for A2A.

[155.27s] To get started with ADK, you can fire up your favorite IDE, then head over to adk.dev, select your language of choice, choose your design patterns, select your models from Model Garden, and get running.

[167.23s] ADK provides a batteries-included toolbox for architecting agents.
[171.09s] But what about agentic-assisted development, or vibe coding?
[174.35s] This is where Agents CLI shines.
[176.65s] It is a full programmatic interface for coding agents which can automate the core tasks of creating and managing ADK agents.
[183.57s] Specifically, it offers agent skills for AI-assisted development, automated evaluation to quickly measure agent efficacy, and automated deployment to Agent Runtimes and the Gemini Enterprise app.

[194.63s] And if you want a low-code visual builder for building agents, then you can use Agent Studio in the Cloud Console.
[200.99s] It lets you map out your agent flows, test them in real time, and see exactly how the model reasons through a conversation.
[207.49s] Once you're happy with the flow, you can deploy it directly to Agent Runtime or export the logic as ADK code, which can then be deployed to Cloud Run, GKE, or anywhere you like.
[217.91s] You can mix and blend your development workflow operating between Agents CLI and Agent Studio, or just write code from scratch the old-fashioned way.

[225.87s] If you don't want to start with a blank IDE, you can find lots of prebuilt agents in Agent Garden to give you a head start.
[231.63s] It's a library of high-quality templates for common enterprise patterns, like financial analysis or marketing campaigns, that you can then deploy and customize as needed.

[240.53s] OK, let's say you made a great agent.
[243.05s] It works on your machine.
[244.21s] Now how do you deploy it and get it running in production?
[247.23s] Well, you can deploy and serve your agent on Agent Runtime.
[251.15s] Agent Runtime is a managed platform as a service specifically designed for the needs of enterprise-ready agents.
[258.07s] For example, it includes less than 1 second cold starts and supports long-running agents that can keep reasoning for up to seven days.
[266.39s] While it's optimized for ADK, Agent Runtime is framework agnostic, so you have the flexibility to deploy agents, built-in LangGraph, LangChain, or your own custom stack.

[276.43s] Now, when an agent is running in a shared environment, it's common to have multiple users, which will each have multiple conversations with the agent.
[283.33s] So how do you manage these?
[285.07s] Agent Sessions keeps track of interactions between a user and agents.
[290.03s] If you're using ADK on Agent Runtime, these are stored and handled automatically.
[294.21s] You can also create custom session IDs, which lets you map interactions directly to your internal customer records or project IDs.

[301.38s] When a user has a lot of interactions with an agent, it's really important for the agent to remember things over time so the user doesn't need to provide this every time.
[309.14s] You can add this capability to your agent using Memory Bank.

[312.78s] If you need your agent to execute code or interact with a UI in some way, like a legacy application that doesn't have an API, then you can use Agent Sandbox to have a safe environment for the agent to do whatever it needs to do.

[324.14s] OK, we're deployed, so that means we're ready to go in production, right?
[327.62s] Well, not exactly.
[328.96s] We need to talk about agent governance.
[331.12s] So why does this matter?
[332.34s] It gives you the safety and control needed to actually trust your autonomous agents with real business tasks, instead of having to constantly babysit them.

[340.30s] When you have autonomous agents acting on behalf of users, we have several problems.
[344.36s] How do we know which agent is taking a specific action?
[347.18s] Agent Identity answers that question.
[349.44s] When you deploy an agent to Agent Runtime, every agent gets its own IAM principle.

[354.46s] Another problem is how to keep track of all the agents spread across Google Cloud.
[358.66s] Agent Registry handles this by automatically cataloging agents deployed to Agent Runtime, GKE, Gemini Enterprise, and Google Workspace.
[366.50s] It also automatically catalogs first-party MCP servers and MCP servers from Apigee.
[371.54s] Additionally, you could register third-party A2A agents and MCP servers, which lets your agents in Google Cloud access them securely.

[378.70s] The next logical problem to solve is access management — which agents have access to specific tools and other agents.
[384.78s] You can set IAM policies on agents, tools, and the registry itself through Agent Policies.

[390.58s] Model Armor templates can be defined, along with Sensitive Data Protection, to sanitize both input prompts and responses from an agent, which blocks prompt injections and PII leaks.

[400.42s] To efficiently scale and enforce these policies, Agent Gateway acts as a single entry point.
[405.54s] It intercepts all ingress and egress calls to audit or enforce the policies.

[410.48s] And because agents aren't always 100% predictable, Anomaly Detection uses an LLM as a judge framework to watch reasoning patterns and flag behavior that looks weird or stalled.
[419.94s] You can see all agent-specific threats in the curated Agent Security Dashboard.

[424.57s] When you're running an agent in production, the quality of responses and actions taken is incredibly important.
[429.78s] However, agents are highly complex systems with nondeterministic behavior, so it can be really difficult to troubleshoot when something goes wrong.
[437.30s] This is what Agent Observability is used for, giving full visibility into agent decision making.
[442.68s] You get turnkey dashboards and automatic tracing to see exactly why an agent made a decision, what tools it called, and where the logic went sideways.

[450.86s] And when you have multi-agent systems or lots of MCP servers, it can be challenging to visualize what all is included in the system.
[457.66s] So you can use Agent Topology to get a graph-like view of all the agents and MCP servers in a system and view aggregated traces for them.

[466.14s] In regular software development, you'll typically write unit or integration tests to verify that the behavior stays consistent when you make a code change.
[473.46s] But unlike traditional software, generative AI is inherently nondeterministic, which makes testing crucial but highly complex.
[480.33s] So this is how you can use Agent Evaluation.
[482.99s] You can automatically evaluate even complex, multi-step interactions.

[487.41s] Taking this a step further, we know that there are infinitely more edge cases to consider when building an AI agent versus deterministic systems, but it's impractical to manually write test cases for all these possibilities.
[498.55s] So you can use Agent Simulation to automatically generate thousands of sample interactions to test with, ideally before you push to prod.

[506.09s] Because we're running at high scale, it can make sense to automate making improvements to our agent over time when failures occur.
[512.57s] This is how you use Agent Optimizer.
[514.83s] It refines your instructions based on failure signals, creating continuous feedback loop designed to improve your agents.

[522.01s] Building enterprise-grade agents doesn't have to mean duct taping a dozen different tools together.
[526.53s] Agent Platform is designed to give you a clean path, from your first lines of code to running securely in production.
[531.95s] Check out the links in the description for official documentation, the GitHub repository, and tutorials to try out for yourself.
[538.15s] We can't wait to see what you build.

---

**End of transcript.**
