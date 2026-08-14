# **W3C Community Group Responses**

## **What problem(s) do you want to solve?**
Organizations involved in healthcare, social care, housing, justice, education, and other human-service domains increasingly need to exchange, integrate, and reason over information that spans multiple care domains. While many standards, information models, and ontologies exist, they are often developed independently and reflect different perspectives, assumptions, and semantic structures. 

As a result, organizations face significant challenges in achieving semantic interoperability, whole-person care coordination, integrated analytics, AI-enabled reasoning, and the development of applications that require semantically consistent information across domains.  This impacts both clinical and social outcomes.  Integration across these domains is essential -- not optional -- for better clinical and social outcomes.  For example, the concept of a Care Plan needs to be reflected in an information model that effectively addresses this problem.  The solution to this problem can be characterized as "Whole Person Care".

## **What is the mission of this Group?**

The mission of the group is to develop a Unified Care Model (UCM): an open, cross-domain ontology for care domains, which facilitates semantic interoperability across healthcare, social care, housing, justice, education, and related human-service ecosystems.  This will enable more effective data exchange, integration, reasoning, and reuse across these domains.  

The UCM will be a high-level ontology that can be used to semantically align and bridge existing domain-specific information models, ontologies, and standards.  The Care Plan is expected to be the most critical component.  The UCM will not replace existing standards.  

Existing inputs and open questions include, but are not limited to:
 - United States Core Data for Interoperability (USCDI) https://isp.healthit.gov/united-states-core-data-interoperability-uscdi
   - Which versions?
   - Relationship to care plan
   - Recommendations for using clinical coding structures in care plan
 - FHIR RDF ontology
 - Semantic gaps in FHIR
 - Proposed Unified Care Model (UCM) Architecture https://github.com/hserv/ucm/blob/main/ucm-design-principles.md

## **Design Principles**

Key design principles -- subject to change by the group -- include:

• UCM to be developed as an OWL ontology supporting Description Logic reasoning.  
• Uses BFO as the ontological foundation.  
• Leverages SULO as a semantic classification framework.  
• Aligns with HL7, HUD, NIEM and other domain artifacts.  
• Uses a layered architecture of Core Concepts, Participation Concepts, and Domain Concepts.  
• Enables independent extension by different subject matter experts while maintaining semantic consistency through a shared core.  
• Emphasizes reuse, extensibility, semantic clarity, and cross-domain interoperability.

## **Will the Group Publish Specifications?**

Yes. The group anticipates producing a W3C Community Group Report, describing the Unified Care Model.  The long-term goal is to use this report as an input or starting point for further standardization efforts.

