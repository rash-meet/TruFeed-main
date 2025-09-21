# TruFeed
Google Agentic AI Day 2025

TruFeed is a real-time civic incident feed platform that transforms scattered citizen reports and social media posts into structured, actionable events. Using AI for analysis, clustering, and verification, it helps communities stay informed about critical issues such as roadblocks, accidents, and infrastructure outages wuth a focus on three categories - Criminal events, Accidents/incidents and Natural Disasters.

---
![Architecture Overview](https://github.com/user-attachments/assets/65adb182-d012-4b82-8206-486bc90d908f)

## Features

### Citizen Reporting
- Web-based submission form with support for media uploads and geolocation
- Reports can also be submitted by posting on social media using the `#TruFeed` hashtag

### AI Analysis
- Vision AI identifies visible elements in uploaded images (e.g., traffic signs, hazards)
- Gemini LLM processes captions to generate summaries and determine sentiment
- Data is enriched with time-of-day estimation, location extraction, and event classification

### Confidence Score
- Confidence score is computed using:
  - Cluster consistency (location, category, content)
  - Report volume and recency
  - Vision and Gemini AI analysis
  - Community voting (upvotes/downvotes)
  - Cross-verification using a RAG (Retrieval-Augmented Generation) agent
- Higher scores indicate stronger likelihood of factual accuracy and reliability

### Live Visualization
- Interactive map displays current and past reports
- Filtering and event type navigation supported

### Community Voting
- Users can vote on reports to surface the most credible or relevant incidents

### integrated Chatbot 
- Users can query and interact with AI chatbot that will be able to answer user specific query

### MCP inetgration
- A basic MCP server (On Cloud Run) has been initialised with agents runnning on Cloud Functions
---

## Architecture Overview

- A FastAPI-based MCP (Multi-Agent Control Plane) deployed on Cloud Run manages the end-to-end workflow.
- Four intelligent agents run as independent Google Cloud Functions:
  - Ingestion Agent
  - Clustering Agent
  - Evaluation Agent
  - Publishing Agent
- A RAG Updation Agent periodically enriches the system with verified data to support scoring.
- Firebase is used for Firestore (NoSQL DB), Cloud Storage (media), and Authentication.
- Frontend and backend are connected through a React-based web app.
- Users can also interact via a Gemini-powered chatbot integrated through Vertex AI.

---

## Running the Agents

Each agent can be:

- Imported and executed in Vertex AI Colab Notebooks
- Deployed independently to Google Cloud Functions

Note: Ensure appropriate access to Google services, and set your project ID and credentials accordingly.

---

## RAG Agent Instructions

The RAG agent verifies the accuracy of clustered event data using external sources.

- Requires access to publicly available datasets in `.txt`, `.md`, or `.pdf` format
- The data must be accessible via a public HTTP(S) link or stored in a public Google Cloud Storage bucket
- The confidence score is generated based on alignment between event content and known facts

