**OVERVIEW**

Build a system where a recruiter logs in to manage job openings and candidates — including AI-powered resume parsing and fit scoring. You own all design decisions: data model, API structure, and UI layout. We are evaluating your thinking, not just the output.

**MODULE 1 — AUTH**

|  |
| --- |
| **Recruiter Login MUST**   * **Register & login —** A recruiter should be able to register and log in securely. * **Protected routes —** All job and candidate actions are accessible only to an authenticated recruiter. How you implement and secure this is your call. |

**MODULE 2 — JOBS**

|  |
| --- |
| **Manage Job Openings MUST**   * **Create and manage —** A recruiter should be able to add, edit, and close job openings. * **List and filter —** Jobs should be easy to browse. Think about what a recruiter actually needs to filter by. |

**MODULE 3 — CANDIDATES**

|  |
| --- |
| **Manage Candidates MUST**   * **CRUD —** A recruiter should be able to add, view, update, and remove candidates linked to a job. * **Resume upload + AI parsing —** Add a candidate by uploading their resume. Use any AI API to extract and structure the key information. * **AI fit scoring —** Automatically score how well the candidate fits the job. Explain why. |

**MODULE 4 — FRONTEND**

|  |
| --- |
| **React UI MUST**   * **Recruiter UI —** Login screen + whatever screens make sense for the workflow. Layout and structure is your call. |

**MODULE 5 — DOCKER**

|  |
| --- |
| **One-command Setup MUST**   * **docker-compose —** The entire app — backend, frontend, and database — must run with a single docker-compose up. No manual setup beyond adding a .env file. |

**AI API — YOUR CHOICE**

|  |
| --- |
| You may use any AI API for resume parsing and fit scoring. Add your chosen API key to .env.example so we can run it. |

**DEPLOYMENT**

|  |
| --- |
| Deploy the full app on any free-tier cloud platform of your choice. Share the live URL along with your submission. Both the backend and frontend should be accessible.  *Note: Free tiers may sleep after inactivity. That is fine — just mention it in your README.* |

**BONUS**

|  |
| --- |
| **Optional — Good to Have BONUS**   * Bulk resume upload — rank multiple candidates by fit score * What I'd improve with more time — a short section in the README |

**TECH STACK**

|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| **FastAPI** | **PostgreSQL** | **JWT Auth** | **Any AI API** | **ReactJS** | **TypeScript** | **Docker** |

**SUBMISSION**

|  |
| --- |
| * GitHub repo (public) with clean commit history * Live deployed URL — backend and frontend both accessible * README with setup steps + .env.example * App must run locally via docker-compose up |

**WHAT WE ARE REALLY EVALUATING**

|  |
| --- |
| Your decisions matter more than the volume of code. How you model the data, secure the APIs, and handle the AI layer tells us more than a perfect UI. The README should reflect your thinking — not just how to run the app. |
