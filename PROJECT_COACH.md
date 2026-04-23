# Project: "Coach" — A Conversational Chess Coach for Ajedrez.ai

**A publishable ML portfolio project targeting Slack's ML Engineer role.**

---

## TL;DR

Build **Coach**, an agentic conversational chess coach layered on top of Ajedrez.ai. You paste in one of your games, and Coach talks you through it: what went wrong, why, what to do next time, and which master games teach the same lesson. Under the hood it's a retrieval-augmented, tool-calling agent that orchestrates Stockfish, a vector database of millions of master-game positions, an XGBoost ranking model for puzzle recommendations, and a fine-tuned BERT model that classifies player weaknesses from move sequences. You publish the code, a technical writeup, a live demo, and eval numbers — a complete artifact that mirrors the exact work Slack does on Slackbot, search, and recommendations.

The crucial point: this is not a chess project with ML bolted on. It is an ML systems project that happens to use chess as the problem domain. Chess is chosen deliberately because it has (a) massive public datasets (Lichess publishes ~100M games/month), (b) a ground-truth oracle (Stockfish) for supervised labels, and (c) a clear conversational product surface that maps directly to Slackbot. Every sentence of the Slack job description has a corresponding component in this project.

---

## Why this project, why Slack

Slack's ML job description says it plainly: "We work on applications across agentic systems (Slackbot), search, recommendation, and more." They want practical ML engineers who deliver business value — "sometimes that means bootstrapping something simple like a logistic regression and moving on. Other times that means developing sophisticated, finely tuned models." They want you to have "put machine learning models or other data-derived artifacts into production at scale."

Most portfolio projects aimed at FAANG fail one of two ways. Either they're a Kaggle notebook with no product, no deployment, no users, no eval harness — just a model. Or they're an over-scoped "disrupt the industry" plan that was never built. Coach threads the needle: it's a focused, shippable system with a clear user-facing product, it uses every technique Slack cares about, and its scope can be genuinely completed by one person in 6–10 weeks of evenings and weekends.

The second-order benefit is that it compounds on what you already have. Ajedrez.ai gives you the web app, the auth, the game storage, the UI shell. Your Handshake AI experience evaluating LLM outputs maps directly to the eval framework Coach needs. Your background as a founder of Nuez IA frames you as someone who ships, not just someone who studies. Coach ties all three strands together into one coherent narrative.

---

## What gets built

Coach is a conversational agent that answers questions about your chess games. The user-visible product is a chat interface embedded in Ajedrez.ai. The user pastes in a PGN or selects one of their recent games, then asks questions like "where did I go wrong," "what should I have played on move 14," "what opening should I study given my weaknesses," or "show me a master game that demonstrates this endgame technique." Coach responds in natural language, grounded in both engine analysis and retrieved master games, with a ranked list of recommended next actions.

Architecturally, Coach has eight components. Each maps to a specific technique Slack's JD asks for.

**1. The agent loop.** A tool-calling orchestrator that decomposes user requests into sub-tasks. When you ask "why did I lose," the agent doesn't just forward the question to an LLM. It identifies the critical moments (via an engine-eval delta threshold), retrieves similar master-game positions, checks your weakness profile, and only then calls the LLM with structured context to generate the explanation. This is the core Slackbot analogy: agentic systems don't just answer, they act. Built in Python using Claude's or OpenAI's tool-calling API.

**2. Position embedding model.** A neural network (PyTorch) that maps a chess position (FEN) to a 128-dimensional embedding where tactically and strategically similar positions cluster together. Trained using contrastive learning on master games: positions from the same game, or positions that Stockfish evaluates similarly, are pulled together; positions from unrelated games are pushed apart. This is the novel, domain-specific ML contribution — and it is exactly the kind of embedding work that powers Slack's own search and recommendation features.

**3. Vector retrieval.** The position embeddings go into pgvector (Postgres extension). Given a user's position, retrieve the 20 most similar master-game positions for grounded commentary. This is the RAG substrate. Slack's JD lists vector databases and embeddings as nice-to-haves; Coach makes them load-bearing.

**4. Weakness classifier.** A fine-tuned BERT model (via Hugging Face Transformers, TensorFlow backend) that takes a sequence of a player's moves (treated as tokens) and classifies recurring weaknesses: do they hang pieces in tactical positions, do they misplay closed positions, are they weak in rook endgames. Trained on labeled games where the label is derived from Stockfish's centipawn-loss pattern across the game. This hits the "fine-tuned BERT models" bullet directly.

**5. Ranking model.** An XGBoost model that ranks recommended puzzles for a given user. Features include user's weakness vector from component 4, puzzle's theme tags, puzzle difficulty rating, the user's recent performance. Labels come from implicit feedback: did the user solve the puzzle, how long did it take, did they return to similar puzzles. This is the "ranking" piece of the JD, and XGBoost is the explicit tool Slack lists.

**6. Batch data pipeline.** Airflow DAGs that ingest Lichess's monthly PGN dumps (they publish ~100M games per month, publicly, free) and produce the training data for components 2, 4, and 5. Pipeline stages: download, parse PGN, extract positions, compute Stockfish evaluations at depth 15, compute features, shard for training. This is the "batch data processing pipelines with tools like Airflow" bullet, with a dataset large enough to be credible at scale.

**7. Generative commentary.** When the agent has assembled context (engine analysis, retrieved similar master games, user's weakness profile), it calls a foundation model (Claude via the Anthropic API) with a carefully engineered prompt to generate the natural-language explanation. This is the GenAI surface. The prompt engineering, the grounding in retrieved context, and the evaluation of output quality are the interesting engineering, not the LLM itself.

**8. Eval harness.** A small but rigorous offline evaluation framework. For a held-out set of 500 games annotated by strong players (sourced from public annotated-games databases and hand-written by you for ~100 positions), measure: does Coach identify the same critical moments, does its recommended alternative move match the annotation, is its explanation factually accurate. Use Claude as an LLM-as-judge for the qualitative dimensions and track metrics over time. This piece is where your current Handshake AI work becomes directly transferable — you have already been doing exactly this kind of structured model evaluation.

---

## Mapping to the Slack job description

This table is the reason the project exists. Every row is a line you can point to in an interview.

| Slack JD requirement | Coach component |
|---|---|
| "ML frameworks like PyTorch, TensorFlow, Keras, XGBoost" | PyTorch for position embeddings, TensorFlow/HF for BERT fine-tune, XGBoost for ranking |
| "Fine tuned LLMs or BERT models" | Component 4: weakness classifier |
| "Building batch data processing pipelines with Airflow" | Component 6: Lichess ingestion DAGs |
| "Put machine learning models into production at scale" | Deployed on Fly.io serving real users via Ajedrez.ai |
| "Ranking, retrieval, and generative AI use-cases" | Components 2+3 (retrieval), 5 (ranking), 7 (generative) — all three explicit |
| "Agentic systems (Slackbot)" | Component 1: the agent loop with tool use |
| "Expertise in conversational agentic systems" | Same — the product surface *is* conversation |
| "Expertise in retrieval systems and search algorithms" | Component 3: vector retrieval over 100M+ positions |
| "Familiarity with vector databases and embeddings" | pgvector, custom-trained position embeddings |
| "Multiple data types in RAG including structured, unstructured, and knowledge graphs" | Structured (positions, engine evals), unstructured (master-game PGNs), knowledge graph (opening tree, ECO classifications) |
| "Broad experience across NLP, ML, and Generative AI" | All three, each driving a user-visible feature |
| "Analytical and data driven mindset, measure success with complicated ML/AI products" | Component 8: eval harness with offline metrics |
| "Write understandable, testable code" | Open source, typed, tested, documented |
| "Explaining complex technical concepts to non-specialists" | The writeup itself is the proof |

---

## Build plan (realistic scope)

This is a 6–10 week side-project plan assuming ~15 hours/week. The critical path is designed so that every phase ends with something publishable on its own. Do not skip to phase 3 before phase 1 is deployed.

### Phase 1 — Minimum Lovable Coach (weeks 1–3)

Build the thinnest version that works end-to-end on one game at a time. No training yet, no ingestion pipeline, no custom models — just the agent loop, a hand-curated set of ~500 master games indexed with off-the-shelf sentence-transformer embeddings on the PGN text, Stockfish for analysis, and Claude for generation.

A user pastes in one of their PGN games and asks "where did I go wrong." Coach identifies the three biggest engine-eval drops, pulls the most similar master-game positions from the 500-game corpus, and generates a grounded three-paragraph explanation with specific move references.

The point of phase 1 is to prove the loop works and to have something deployed within three weeks. Publish phase 1 standalone. Live demo URL, GitHub repo, a 1500-word writeup titled something like "I built a conversational chess coach in three weekends — here's how." Post to Hacker News, r/chessprogramming, r/SideProject. This alone is a credible ML portfolio piece.

### Phase 2 — Custom Embeddings and Batch Pipeline (weeks 4–6)

Now replace the off-the-shelf embeddings with a trained position-embedding model (PyTorch, contrastive learning on 1M positions). Stand up the Airflow pipeline that ingests one month of Lichess data. Move to pgvector with a proper index. Add a simple weakness classifier — start with logistic regression on hand-crafted features (mirroring Slack's "bootstrap a logistic regression and move on" ethos), not BERT yet. Measure retrieval quality on a held-out set of annotated positions.

Publish phase 2 as the second writeup: "Training chess-position embeddings with contrastive learning — and why they beat sentence-transformers." This one is more technical, more interesting to ML researchers, and will get picked up in ML newsletters if it's honest and specific.

### Phase 3 — BERT Fine-tune, XGBoost Ranker, Eval Harness (weeks 7–10)

Fine-tune distilBERT on move sequences for weakness classification. Build the XGBoost puzzle ranker trained on Lichess-puzzle implicit feedback data (which is publicly available). Stand up the eval harness with 500 annotated positions, track metrics over time, and publish quantitative results.

Publish phase 3 as the capstone writeup: "What I learned training four models for one product — an honest retrospective." This is the piece that goes on the resume and into the Slack cover letter.

---

## Publication plan

The project lives in three places, and each has a specific audience.

**GitHub repo (`ajedrez-ai/coach`).** Open source, MIT license. Well-organized, typed, tested, documented. README leads with a 30-second demo GIF, followed by architecture diagram, followed by links to the writeups. The code is the proof. Recruiters and hiring managers will click through it; make sure it rewards the click. Pinned at the top of your GitHub profile.

**Technical writeups (personal blog or Medium).** Three posts, one per phase, each 1500–2500 words with honest tradeoffs and concrete numbers. Don't embellish. The Slack hiring team has read a thousand "I built an LLM app" posts; they can smell exaggeration. What lands is specificity — "the off-the-shelf embeddings had 42% recall@10 on our annotated test set, the custom model hit 67%, here's what changed" beats "I built a production-grade retrieval system" every time.

**Live demo.** Deployed at `coach.ajedrez.ai` or equivalent. This is the single most important artifact for the Slack application. Interviewers who click a live demo and have it work on the first try form an impression no resume bullet can match. Keep it fast, keep it mobile-responsive, and have a "try this sample game" button so they don't have to find a PGN.

**Distribution channels.** For each writeup, post to: Hacker News (Show HN), r/MachineLearning (as a project post, follow their strict rules), r/chess and r/chessprogramming, LinkedIn with a personal framing, Twitter/X thread with screenshots. Mention it in a short cold email to a Slack ML engineer on LinkedIn — one sentence ask: "I built this project specifically inspired by your team's work on Slackbot, would you have 15 minutes to give me feedback?" That email has a dramatically higher response rate than a blind application.

---

## What this gets you, honestly

Shipping phase 1 alone puts you in the top 10% of ML portfolio projects recruiters see. Shipping all three phases with quantitative eval numbers and real writeups puts you in the top 1%. Neither guarantees a Slack offer — ML hiring is brutal and partially stochastic — but both dramatically improve your odds, and the project is useful regardless of outcome because it compounds. If Slack doesn't work out, Coach is exactly the kind of artifact that gets you interviews at Anthropic, OpenAI, Perplexity, or any other conversational-AI company.

What it does *not* get you: an ML research reputation, credit for novel algorithms, or the ability to claim you've "built systems serving millions." Don't overstate any of that. The honest pitch is "I built a production-quality conversational ML system end-to-end, including the boring parts like data pipelines and eval harnesses, and I have the live demo and metrics to prove it." That pitch is strong and true.

---

## The single most important piece of advice

Publish phase 1 the moment it works, even if you're embarrassed by the gaps. Three shipped phases over ten weeks beats one perfect capstone eight months from now. Slack's JD says "practical machine learning team, not a research team." Prove you can ship. Then prove you can keep shipping. The writeups will be better, the code will be cleaner, and your thinking will be sharper by phase 3 — let the audience see that growth rather than hiding it.

Ship ugly. Publish fast. Iterate in public. That is the engineer Slack is hiring.
