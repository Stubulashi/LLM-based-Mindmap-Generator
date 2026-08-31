# Use of AI — AI-Assisted Tools & Workflow

## Overview

This document discloses how AI-assisted tools were used during the development of the project, grouped into a small number of work blocks rather than enumerated as an exhaustive itemized list. A general position is stated up front: AI tools served primarily as *support* in this process. They helped review, search, critique, and suggest, while the design decisions, the implementation choices, the code itself, and its verification remained the responsibility of the human developer. The technology was engaged as a companion that accelerated and stress-tested the work, not as an autonomous author of it.

## Tools Used

The main language model tooling used in the project included: DeepSeek (v4-flash and v4-pro), DeepL, Qoder, Gemini, and GPT. DeepL was used for language-level verification, while the remaining tools served different purposes across the work blocks described below. DeepSeek, in both variants, was the workhorse for daily programming assistance; Qoder was the integrated development environment that hosted much of that assistance; Gemini and GPT were used for breadth-oriented exploration and review at the planning stage. Where a variant was chosen (flash or pro), the choice reflected the type of task being handled: lighter variants for routine interactions, heavier variants for more demanding analysis.

## Planning and Feasibility Work

During the early stage, before any code was written, several details of the project proposal were discussed at length with an LLM, covering a more concrete feasibility assessment, the anticipated difficulties, and, in places, the ordering of the work. In parallel, a reverse-role mode of thinking was adopted: the model was asked to act as an external reviewer and pose detailed questions about specific points, so that the resulting understanding could be checked for correctness and plausibility rather than being taken at face value. Prompt instructions were deliberately worded to avoid producing concrete examples in code, so that ready-made cases would not steer the analysis toward a fixed line of reasoning, the so-called "fixed mindset" problem. The same LLM also helped to narrow the scope worth investigating: it assisted in refining the candidate models, clarifying the available development directions, and weighing the effort involved, and it helped to evaluate and set aside features or approaches that appeared unnecessary or too divergent. Finally, the LLM was requested to search the web for existing open-source projects or Git repositories, so that prior work could serve as a reference and as a source of reusable ideas rather than being reinvented from scratch.

## Code Assistance

DeepSeek was the primary LLM used for programming assistance throughout the implementation phase. In particular, the v4-flash variant was connected through the Qoder IDE, where it provided real-time code review, error correction, and suggestions for the next steps while coding, shortening the feedback loop of writing and revising code. During this period, the DeepSeek harness feature was also released and was experimented with; the results produced by it were used to double-check the code. For personal reasons, however, this feature turned out to be of limited benefit to the present project, and it was therefore not adopted as a main workflow step.

Because the integrated development environment exposes an overview of all files in the workspace, the sidebar ("Quest") mode of the IDE was used for cross-file analysis: tracking the nesting relationships between functions and the reference chains of variables across the repository. The same mode was also used to produce and archive daily or per-phase working logs during the project.

With respect to the runtime environment, the university cluster was still unfamiliar and still being learned at the time, so it was not yet a reliable channel for model calls. As a result, all LLM-related calls, including the ones driven by the Qoder IDE environment or by agents, came from the DeepSeek API. Different variants (flash and pro) were selected according to the purpose and the scope of each call.

## Frontend and Rendering Integration

The team had limited experience with front-end development and did not yet have a reliable ability to link the front end and the back end through a FastAPI stack. As a consequence, the rate of LLM usage was relatively high in the frontend portion of the work. This became most noticeable when the frontend mind-map rendering was later migrated to the AntV G6 system, which was new to the team. Integrating that system involved understanding an unfamiliar rendering model, adapting the data flow, and debugging the resulting interactions, and the LLM played a large role in each of those steps. The contribution there is estimated at roughly 70%. It should be stressed that this is an approximate figure reflecting chiefly the rendering-integration step; it is not a statement about the contribution to the project as a whole.

## Concluding Note

Taken together, the use of AI tools was concentrated in three areas: early planning and scoping, code review and assistance within the IDE, and the integration of an unfamiliar rendering library. In every case, the output was reviewed, adjusted, and verified by the developer before being accepted. The tools multiplied the speed at which the work could be explored, but the decisions about what to accept, what to discard, and what to change remained human ones throughout.
