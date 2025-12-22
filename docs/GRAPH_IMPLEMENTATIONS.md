# Graph Implementation Architectures

This document visualizes the three different LangGraph architectures found in this workspace.

## 1. Iterative Search Graph (Local)
**File:** `backend/src/agent/graph.py`
**Type:** Flat Graph with Parallel Fan-out
**Goal:** Answer a specific question through iterative refinement.

```mermaid
graph TD
    classDef conditional fill:#f9f,stroke:#333,stroke-width:2px;
    classDef node fill:#fff,stroke:#333,stroke-width:2px;
    
    START((Start)) --> generate_query[Generate Query]
    generate_query --> planning_mode[Planning Mode]
    
    planning_mode --> check_plan{Planning Router}
    class check_plan conditional
    
    check_plan -- "/plan" --> planning_wait[Planning Wait]
    check_plan -- "/confirm" or "/end_plan" --> fan_out_research((Fan Out))
    
    planning_wait --> check_plan_wait{Planning Router}
    class check_plan_wait conditional
    check_plan_wait -- Wait --> planning_wait
    check_plan_wait -- Confirm --> fan_out_research
    
    fan_out_research --> web_research[Web Research]
    
    subgraph Parallel Execution
        web_research
    end
    
    web_research --> validate_web_results[Validate Results]
    validate_web_results --> reflection[Reflection]
    
    reflection --> evaluate{Evaluate Research}
    class evaluate conditional
    
    evaluate -- "Is Sufficient / Max Loops" --> finalize_answer[Finalize Answer]
    evaluate -- "Knowledge Gap" --> fan_out_research
    
    finalize_answer --> END((End))
```

## 2. Section-Based Report Graph (Legacy)
**File:** `src/legacy/graph.py`
**Type:** Map-Reduce Style with Subgraphs
**Goal:** Write a structured report by researching sections in parallel.

```mermaid
graph TD
    classDef conditional fill:#f9f,stroke:#333,stroke-width:2px;
    classDef subgraph_node fill:#e1f5fe,stroke:#01579b,stroke-width:2px;

    START((Start)) --> generate_report_plan[Generate Report Plan]
    generate_report_plan --> human_feedback[Human Feedback]
    
    human_feedback --> check_feedback{Check Feedback}
    class check_feedback conditional
    
    check_feedback -- "Changes Requested" --> generate_report_plan
    check_feedback -- "Approved" --> fan_out_sections((Fan Out Sections))
    
    subgraph "Section Subgraph (Parallel)"
        fan_out_sections --> generate_queries[Generate Queries]
        generate_queries --> search_web[Search Web]
        search_web --> write_section[Write Section]
        
        write_section --> check_quality{Check Quality}
        class check_quality conditional
        
        check_quality -- "Needs More Info" --> search_web
        check_quality -- "Pass" --> section_complete((Section Complete))
    end
    
    section_complete --> gather_completed_sections[Gather Completed Sections]
    
    gather_completed_sections --> initiate_final{Initiate Final Writing}
    class initiate_final conditional
    
    initiate_final --> write_final_sections[Write Final Sections]
    write_final_sections --> compile_final_report[Compile Final Report]
    compile_final_report --> END((End))
```

## 3. Hierarchical Deep Research Graph (New)
**File:** `src/open_deep_research/deep_researcher.py`
**Type:** Hierarchical Multi-Agent (Supervisor-Worker)
**Goal:** Conduct deep, autonomous research with managed teams.

```mermaid
graph TD
    classDef conditional fill:#f9f,stroke:#333,stroke-width:2px;
    classDef supervisor fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef worker fill:#e1f5fe,stroke:#01579b,stroke-width:2px;

    START((Start)) --> clarify_with_user[Clarify With User]
    
    clarify_with_user --> check_clarity{Check Clarity}
    class check_clarity conditional
    
    check_clarity -- "Need Info" --> END_QUESTION((End: Ask User))
    check_clarity -- "Clear" --> write_research_brief[Write Research Brief]
    
    write_research_brief --> supervisor_node[Research Supervisor]
    class supervisor_node supervisor
    
    subgraph "Supervisor Subgraph"
        supervisor_node --> supervisor_tools[Supervisor Tools]
        class supervisor_tools supervisor
        
        supervisor_tools --> check_sup_action{Action?}
        class check_sup_action conditional
        
        check_sup_action -- "Think" --> supervisor_node
        check_sup_action -- "Delegate" --> fan_out_researchers((Fan Out Researchers))
        check_sup_action -- "Complete" --> supervisor_end((Supervisor End))
        
        subgraph "Researcher Subgraph (Parallel)"
            fan_out_researchers --> researcher[Researcher Agent]
            class researcher worker
            
            researcher --> researcher_tools[Researcher Tools]
            class researcher_tools worker
            
            researcher_tools --> check_res_action{Action?}
            class check_res_action conditional
            
            check_res_action -- "Search/Think/MCP" --> researcher
            check_res_action -- "Complete" --> compress_research[Compress Research]
            class compress_research worker
            
            compress_research --> researcher_end((Researcher End))
        end
        
        researcher_end --> supervisor_tools
    end
    
    supervisor_end --> final_report_generation[Final Report Generation]
    final_report_generation --> END((End))
```
