# Backlog — Ideas

Ideias soltas, não-aprovadas para release. Documentação informal. Nada aqui autoriza
implementação.

## Convenções

- Cada ideia é um bullet de uma frase. Detalhar só se a ideia avançar para `candidates.md`.
- Ideias podem ser removidas a qualquer momento se forem rejeitadas ou virarem release.
- Não há ordem. Não há prioridade. Não há owner.

## Ideias atuais

(vazio — popular conforme operador ou agentes especialistas tragam ideias)

###############################################################################################
###############################################################################################


### Review of Hooks and rules and commands.



###############################################################################################
###############################################################################################

# Full review of agents

## 1. New agents to be created

### 1.1. The `Project Manager`

The `project-manager`is the master/amestro.
- Acts like a dispatcher. Acts like a router. 
- Reads requests, do a dadaia-grill-me do solve any question, inconsistency our vagueness / ambiguity of the request being asked by the user.
- He's the orchestrator. He must be optimized to be the maestro / orchestrator.
- Right now, many of this orchestration workload is being done by the **product-engineer**.
- It's needed to bring this reponsability to the`project-manager`.
- The **project-manager** ochestrate all the other agents. He give the orders.
- project-manager is specialist on our **multi-agentic workflows**.
- project-manager nows how every flow works, including:
    - How new demands come to the projects and how agents are prepared for handling it.
    - **project-manager** knows very well their agent workesr, what is the attribution of each one.
    - **project-manager** is the one who receives a new demand. 
    - Always a new demand arises **project-manager** do dadaia-grill-me session to understand better what is being demanded.
    - **project-manager** know very weel each one of its agents. And now exactly when to request them for a certain task.
    - **project-manager** is very concious that he employees AI agents. So he is specialist on agentic entities such as `skills`, `hooks`, `rules`, `agentic orchestration workflows`.
- The **project-manager** is the orchestrator. If thare are divergences, he mediates, try to solve. And if it's hard he asks to me. Me the user, the Stakeholder.

#### Review of all workflows and agents are now needed
- A very rigorous review must be done in our actual **agents** and **multi-agentic workflows** inside the lib `dadaia-workspace`.

Our workflows have a big problem right now, they are very confuse. 
- Even me, that have created them are being not able to distinguish between what I call.
- Every time I'm trying to use multi agents for some demand, I prompt what he who will do what. Workflows are not being able of being reutilized.
- Now that we have a professional orchestrator, the project-manager, we need to review deeply this workflows and change them if needed.

**Important**: The **project-manager** agent is will coordinates the team of other agents. 
He is the boss.
- He needs to know very well about the agents (its employees) and the workflows. It's a paralell the real project-managers must know very well their employees and the company workflows. And how to trigger and supervise this workflows made by multiple imployees.

**Skils**: The project manager have the skills related with project management. He master the skills in theory and know which points he must inspect and memoryze about their agents and multi-agentic ochestration workflows.

#### What he can do
- The project manager can spawn other agents and subagents managing them for a specific workfload.
- The project manager can read specs to be aware about what is that project. Understands very well our SDD pattern being used.
- Has all the skills he need to coordinate, supervise and delegate tasks. Is the real manager every company needs.

- He cannot edit code our edit Specs, or anything like that. He does what project-managers do. Coordinate its employees.

### The `Code Reviewer`

- Create an agent for code review.
- It'll use Sonnet 4.6. Can analyze the code based on 
- Does code review that is highly oriented to the architecture and design of the code.
- Always verify the tests executed and coverage and also the quality of the tests designed by the qa-engineer.
- Can be triggered by the `project-manager` or by the `project-auditor` when they need to review the code for some reason.
- Can read implementation, can verify CI/CI job results (logs, etc.) Analyze Specs and implementation in the PR opened.

### The agent `Researcher`
- Create an agent for research.
- The researcher is dispatched by the `project-manager` and by the `project-auditor` when they need to do any research on code.
- The researcher is optimized to work with Sonnet 4.6 and do excellent summarization when agents need a good research to be done.
- THe architect can also dispatch the researcher when he needs to do some research on the
- Can only read and summarize. Can also use WebFetch and WebSearching to research on the web when needed.


### The agent `security-reviewer`
- Create an agent for security review.
- Can only read code and specs. Scan the projects and environment searching for vulnerabilities.
- Has high knowledge about security best practices, most common vulnerabilities, OWASP top 10. E sabe muito bem como usar ferramentas de análise de segurança para identificar vulnerabilidades em código e infraestrutura.
- Can be dispatched by the `project-manager` or by the `project-auditor`.


### 1.2. The `Project Auditor`
- Creation of new agent **project-auditor**.
- Can dispatch other agents. For example: Researcher, code-reviewer, security-reviewer, qa-engineer, designer-specialist. Every agent he needs to produce reports / evidences that he'll use for his audits and to generate his final audit report.

- This agent is specialist in read and understand very well Code (implementation) and Specs.
- He's specialist and analyzing if the Specs are no concise or if they are vague.
- He's the one that is always searching for drifts between the specs and toe implementation.
- He knows very well the processos, meaning that he knows that the memory session inside specs must be very well scanned and compared with the real implementation of the project.
- He knows that the memory session where we have product, architecture and tech-stack is the place where the production project is hosted, meaning, what we see on memory are is the project in it's atomic and actual blueprint. Always that a specs is translated on plan and tasks. When the tasks are finished and tested and approved, then the memory session is updated.
- HE SEARCH ALWAYS, IT'S HIS PRIORITY, TRYING TO IDENTIFYING DRIFTS BETWEEN MEMORY AND IMPLEMENTATION.
- HE IS ALWAYS WHILE HE'S SCANNING THE IMPLEMENTATION REVIEWING SEARCHING FOR DEAD / STALE CODE. THIS IS HIS SECOND MOST IMPORTANT TASK.

The agent `project-auditor` can only read Specs, Read implementation and delegate tasks for the qa-engineer for executing tasks and create evidences:
- Then the `project-auditor` review the evidences.

For example, the `project-auditor` is responsible for an audit to the redacted-slug website.
- While hi's doing its audit he will consult the evidences of the E2E tests produced by the qa-engineer.

Here we have a clear pattern where if **project-auditor** have now the evidences, e asks and the project-manager must delegate the qa-engineer to produce them.

**project-auditor** only writes reports. He don't do anything else.
- Its role is to audit, scan deeply, search for drifts and if specifications are following the pattern.
- Generates a report about the review, points of attention, suggestions and critical problems.
- At the end the report give a score from 1 to 10 about the compliance of that project, meaning how well it's following what should be done.


### 1.3. The Designer-Specialist

- Our frontend-engineer is overloaded with many aspecs that we must take care on frontend implementation. And he's not being able to deliver good experiences on the frontends in a UX/UI meaning. We need the gui responsible for UX/UI.
- Our frontends need indentity and most of all, they need to be responsive, functional and user experience has to be improved.
- Now we are creating the design-specialist.
- The design-specialist read prints for implemented frontends, to validate the UXUI patterns implemented. He consumes these prints generated by qa-engineer as evidence.
- He can only write reports, work on reviews of frontends, and create scatches using specilized tools like Figma and Claude Design tools.
- He has and always search for good patterns for the kinds of frontends that we have.
- For example, He knows that we have a redacted-slug, He knows the kind of frontend we use on redacted-slug and also he knows very well the kind of frontend we use on dadaia-workspace panel.
- And he's specialist and searching and fetching some excelent references that he uses for our work. He knows well that We cannot try to invent the wheel .We need to have always good references. Be original but with excelent references and using them.



 And now we need to review the workflows and make sure they are adapted to use the `project-manager` as the orchestrator agent. 

The orchestrator agent now created and named `project-manager` has in it's team the agents:

### Passive
1. software-architect: Specialist on Software architecture best practices. Receives new demands or can be demanded by other agents to do reviews. He only writes reports. But is specialist in:
- Understand the architecture of what is implemented. Verify the Specs memory sessions to see if the architecture and product and tech-stack are being thruly represented in the documentation.
2. cyber specialist: 


### Hybrid: 
- More passive but in specific domains they can work.

#### 3. devops-engineer: 

Responsible for the compliance of gitflow best practices and CI/CD deployment pipelines.
- Also specialist in terraform and docker. 
- He nows very well how to create infra on the cloud with terraform when it's needed.
- Specialist on databricks and mainly AWS. The best on creating CiCd pipelines on github actions for deploying AWS and Databricks resources using terraform and Github actions Jobs.

**Role**
- Do rigorous audits to verify compliance of gitflow and CI/CD use in each project. 
- The unique responsible for editing files inside the .github/workflows.
- Meaning he is the only one that creates and maintain github actions CI/CD pipelines.

### Actives

#### 1. software-engineer: 
- Already defined. Just mentioning.

#### 2. backend-engineer: 
- Specialist in backend in GOlang.
- It's already configured but it's impotant and overview to verify if thare some improvement points. Or problems with attributions and 

###



#### Feature Dadaia-workspace academy.

- See how it's working now.
- Replace the use of markdown by HTML like the reports.
- Review courses content and the architecture.
- Serve this knowledge on the dadaia-workspace panel
- A new tab named "academy" must be created on dadaia-workspace-panel.
- There the HTMLs with the content for