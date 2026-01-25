---
name: doc-coauthoring
description: Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This workflow helps users efficiently transfer context, refine content through iteration, and verify the doc works for readers. Trigger when user mentions writing docs, creating proposals, drafting specs, or similar documentation tasks.
---

# Doc Co-Authoring Workflow

This skill provides a structured workflow for guiding users through collaborative document creation. Act as an active guide, walking users through three stages: Context Gathering, Refinement & Structure, and Reader Testing.

## When to Offer This Workflow

**Trigger conditions:**

- User mentions writing documentation: "write a doc", "draft a proposal", "create a spec", "write up"
- User mentions specific doc types: "PRD", "design doc", "decision doc", "RFC"
- User seems to be starting a substantial writing task

**Initial offer:**
Offer the user a structured workflow for co-authoring the document. Explain the three stages:

1. **Context Gathering**: User provides all relevant context while Claude asks clarifying questions
2. **Refinement & Structure**: Iteratively build each section through brainstorming and editing
3. **Reader Testing**: Test the doc with a fresh Claude (no context) to catch blind spots

## Stage 1: Context Gathering

**Goal:** Close the gap between what the user knows and what Claude knows.

### Initial Questions

1. What type of document is this? (e.g., technical spec, decision doc, proposal)
2. Who's the primary audience?
3. What's the desired impact when someone reads this?
4. Is there a template or specific format to follow?
5. Any other constraints or context to know?

### Info Dumping

Encourage the user to dump all the context they have:

- Background on the project/problem
- Related team discussions or shared documents
- Why alternative solutions aren't being used
- Organizational context (team dynamics, past incidents, politics)
- Timeline pressures or constraints

## Stage 2: Refinement & Structure

**Goal:** Build the document section by section through brainstorming, curation, and iterative refinement.

For each section:

1. **Clarifying Questions** - Ask 5-10 clarifying questions
2. **Brainstorming** - Brainstorm 5-20 options
3. **Curation** - User indicates what to keep/remove/combine
4. **Gap Check** - Ask if anything important is missing
5. **Drafting** - Draft the section based on selections
6. **Iterative Refinement** - Use `str_replace` for edits

## Stage 3: Reader Testing

**Goal:** Test the document with a fresh Claude (no context bleed) to verify it works for readers.

1. **Predict Reader Questions** - Generate 5-10 questions readers would ask
2. **Test with Sub-Agent** - Test questions with fresh Claude instance
3. **Run Additional Checks** - Check for ambiguity, false assumptions, contradictions
4. **Report and Fix** - Fix any gaps found

## Final Review

- Recommend final read-through by user
- Suggest double-checking facts, links, or technical details
- Verify it achieves the intended impact
