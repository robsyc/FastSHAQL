<!-- https://w3c.github.io/data-shapes/shacl12-core/ — W3C editors' draft, fetched 2026-08-31 -->

This document defines the Core of SHACL.

SHACL, the Shapes Constraint Language, is a language for describing the structure of RDF graphs.
SHACL can be used to define classes and the properties that instances of these classes can have.
More general than classes and instances, SHACL introduces the notion of shapes
that can formally specify constraints on the structure of RDF nodes and edges.
SHACL shapes are themselves represented in RDF graphs called shapes graphs.
The RDF graphs that are described by a shapes graph are called data graphs.

SHACL may be used for a variety of purposes such as
validating, inferencing, modeling domains, generating ontologies to inform other agents,
building user interfaces, generating code, and integrating data.

## SHACL Specifications

This specification is part of the SHACL 1.2 family of specifications. See the [SHACL 1.2 Overview](https://w3c.github.io/data-shapes/shacl12-overview/) for a more detailed introduction to them.

The specifications are as follows:

**Working Drafts:**

[SHACL 1.2 Core](https://www.w3.org/TR/shacl12-core/)
:   defines the Core of SHACL

[SHACL 1.2 Inference Rules](https://www.w3.org/TR/shacl12-inference-rules/)
:   defines SHACL's framework of rule-based inference

[SHACL 1.2 Node Expressions](https://www.w3.org/TR/shacl12-node-expr/)
:   defines expressions used to derive focus nodes and value nodes in SHACL

[SHACL 1.2 Profiling](https://w3c.github.io/data-shapes/shacl12-profiling/)
:   defines the use of SHACL for profiling data, including SHACL data

[SHACL 1.2 SPARQL Extensions](https://www.w3.org/TR/shacl12-sparql/)
:   defines SPARQL-related extensions of SHACL

[SHACL 1.2 UI](https://w3c.github.io/data-shapes/shacl12-ui/)
:   defines SHACL's use for User Interface generation

**Working Group Note Drafts:**

[SHACL 1.2 Overview](https://w3c.github.io/data-shapes/shacl12-overview/)
:   overviews the set of SHACL specifications

[SHACL 1.2 Compact Syntax](https://w3c.github.io/data-shapes/shacl12-cs/)
:   defines an RDF syntax for expressing SHACL concepts

**Note:** Implementers can partially check their level of conformance with the above specifications by successfully passing
the test cases of the [SHACL 1.2 test suite](https://github.com/w3c/data-shapes/tree/gh-pages/shacl12-test-suite).
Note, however, that passing all the tests in the test suite does not imply complete conformance to the specifications.
It only implies that the implementation conforms to the aspects tested by the test suite.

## Document Outline

The introduction includes a [Terminology](#terminology) section.

Sections 2 and 3 cover SHACL shapes and constraints, as well as property paths.

Section 4 introduces node expressions, while section 5 defines validation in SHACL.

Section 6 defines the built-in SHACL Core constraint components, and section 7 discusses non-validating properties.

The syntax of SHACL is RDF.
The examples in this document use Turtle rdf12-turtle and JSON-LD json-ld.
Other RDF serializations such as RDF/XML may be used in practice.
The reader should be familiar with basic RDF concepts rdf12-concepts such as triples.

## 1. Introduction

This document specifies the Core of SHACL (Shapes Constraint Language), a language for describing and validating RDF graphs.
This section introduces SHACL with an overview of the key terminology and an example to illustrate basic concepts.

### 1.1 Terminology

Throughout this document, the following terminology is used.

Terminology that is linked to portions of RDF 1.2 Concepts and Abstract
Syntax is used in SHACL as defined there. Terminology that is linked to
portions of SPARQL 1.2 Query Language is used in SHACL as defined there. A
single linkage is sufficient to provide a definition for all occurrences of a
particular term in this document.

Definitions are complete within this document, i.e., if there is no rule to
make some situation true in this document then the situation is false.

This document uses the terms
RDF graph,
RDF triple,
IRI,
literal,
datatype,
base direction,
blank node,
triple term,
reifier,
node of an RDF graph,
RDF term,
subject,
predicate, and
object of RDF triples
as defined in RDF 1.2 Concepts and Abstract Syntax rdf12-concepts.
Language tags are defined as in BCP47.

A property is an IRI.
An RDF term `n` has a value `v`
for property `p` in an RDF graph if there is an RDF triple in the graph
with subject `n`, predicate `p`, and object `v`.
The phrase "Every value of P in graph G ..." means "Every object of a triple in G with predicate P ...".
(In this document, the verbs *specify* or *declare* are sometimes used to express the fact that an RDF term has values for a given predicate in a graph.)
  
SPARQL property paths are defined as in SPARQL 1.2.
An RDF term `n` has value `v` for SPARQL property path expression
`p` in an RDF graph `G` if there is a
solution mapping in the result of the SPARQL query
`SELECT ?s ?o WHERE { ?s p' ?o }` on `G` that binds `?s` to
`n` and `?o` to `v`, where `p'` is SPARQL surface syntax for `p`.

A SHACL list in an RDF graph `G` is an IRI or a blank node
that is either `rdf:nil` (provided that `rdf:nil` has no value
for either `rdf:first` or `rdf:rest`), or has exactly one value
for the property `rdf:first` in `G` and exactly one value
for the property `rdf:rest` in `G` that is also a SHACL list in `G`,
and the list does not have itself as a value of the property path `rdf:rest+` in `G`.
  
The members of any SHACL list except `rdf:nil` in an RDF
graph `G` consist of its value for `rdf:first` in `G` followed by
the members in `G` of its value for `rdf:rest` in `G`.
The SHACL list `rdf:nil` has no members in any RDF graph.

A node `Sub` in an RDF graph is a SHACL subclass of another node `Super`
in the graph if there is a sequence of triples in the graph each with predicate `rdfs:subClassOf` such that the subject of the first triple is `Sub`,
the object of the last triple is `Super`, and the object of each triple except the last is the subject of the next.
If `Sub` is a SHACL subclass of `Super` in an RDF graph then `Super`
is a SHACL superclass of `Sub` in the graph.

The SHACL types of an RDF term in an RDF graph is the set of its values for `rdf:type` in the
graph as well as the SHACL superclasses of these values in the graph.
Note that some SHACL implementations can be parameterized so that the `rdfs:subClassOf` triples
that determine the SHACL subclasses may be queried from the shapes graph in addition to the data graph.
See [6.3 Graph for rdfs:subClassOf Triples](#subClassOfInShapesGraph).

Nodes in an RDF graph that are subclasses, superclasses, or types of nodes in the graph are referred to as SHACL class.

A node `n` in an RDF graph `G` is a SHACL instance of a SHACL class `C` in `G`
if one of the SHACL types of `n` in `G` is `C`.

For a node `n` in a graph `sourceGraph`,
the deep copy of `n` in a graph `targetGraph`
is `n` in `targetGraph` plus, if `n` is a blank node,
any triples from `sourceGraph` that can be reached by transitively traversing
the blank nodes that appear in the object position of a triple that can be reached
starting with `n` as the subject. This is similar to
the [Concise Bounded Description](https://www.w3.org/submissions/CBD/), but without reification.

### 1.2 Document Conventions

Within this document, the following namespace prefix definitions are used:

| Prefix | Namespace |
| --- | --- |
| `owl:` | `http://www.w3.org/2002/07/owl#` |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` |
| `sh:` | `http://www.w3.org/ns/shacl#` |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` |
| `ex:` | `http://example.com/ns#` |

Within this document, the following JSON-LD context is used:

```
{
  "@context": {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "sh": "http://www.w3.org/ns/shacl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "ex": "http://example.com/ns#"
  }
}
```

Note that the URI of the graph defining the SHACL vocabulary itself is equivalent to
the namespace above, i.e., it includes the `#`.
References to the SHACL vocabulary, e.g., via `owl:imports` should include the `#`.

Throughout the document, color-coded boxes containing RDF graphs in Turtle, JSON-LD and SHACL-C will appear.
These fragments of Turtle documents use the prefix bindings given above.
The JSON-LD document fragments use the context given above.
Only the Turtle documents may highlight certain parts.
*The SHACL-C specification is unstable - SHACL-C document fragments in this document are informative*

```
# This box represents an input shapes graph

<s> ex:p <o> .
						
```

```
# This box represents an input data graph.
# When highlighting is used in the examples:

# Elements highlighted in blue are focus nodes
ex:Bob a ex:Person .

# Elements highlighted in red are focus nodes that fail validation
ex:Alice a ex:Person .
					
```

```
# This box represents an output results graph
					
```

Grey boxes such as this include syntax rules that apply to the shapes graph.

`true` denotes the RDF term `"true"^^xsd:boolean`.
`false` denotes the RDF term `"false"^^xsd:boolean`.

### 1.3 Conformance

This document defines the **SHACL Core** language, also referred to as just **SHACL**.
This specification describes conformance criteria for:

- **SHACL Core processors** as processors that support validation with the SHACL Core Language

This document includes syntactic rules that shapes and other nodes need to fulfill in the shapes graph.
These rules are typically of the form *A shape must have...* or *The values of X are literals* or *All objects of triples with predicate P must be IRIs*.
The complete list of these rules can be found in the [appendix](#syntax-rules).
Nodes that violate any of these rules are called ill-formed.
Nodes that violate none of these rules are called well-formed.

A shapes graph is well-formed if all of the following conditions hold:

1. It contains no ill-formed nodes (i.e., all nodes satisfy the syntax rules mentioned above).
2. Its import closure (as determined by transitively following
   `owl:imports` statements)
   satisfies the constraints defined by Section 3.4 of the OWL 2 syntax specification owl2-syntax, namely that it does not contain two shapes graphs where:
   - they are different versions of the same series
     (i.e., they share the same shapes graph IRI but have different
     `owl:versionIRI` values), or
   - one contains an `owl:incompatibleWith` annotation whose value is equal to
     either the shapes graph IRI or the `owl:versionIRI` of the other.

A shapes graph that is not well-formed is ill-formed.

### 1.4 Relationship between SHACL and RDFS inferencing

SHACL uses the RDF and RDFS vocabularies, but full RDFS inferencing is not required.

However, SHACL processors MAY operate on RDF graphs that include entailments sparql12-entailment,
whether pre-computed before being submitted to a SHACL processor or performed on the fly as
part of SHACL processing (without modifying either data graph or shapes graph).
To support processing of entailments, SHACL includes the property
`sh:entailment` to indicate the inferencing that is required
by a given shapes graph.

The values of the property `sh:entailment` are IRIs.
Common values for this property are covered by sparql12-entailment.

SHACL implementations MAY, but are not required to, support entailment regimes.
If a shapes graph contains any triple with the predicate `sh:entailment` and object `E`
and the SHACL processor does not support `E` as an entailment regime for the given data graph,
then the processor MUST signal a failure.
Otherwise, the SHACL processor MUST provide the entailments for all of the values of `sh:entailment` in the shapes graph,
and any inferred triples MUST be returned by all queries against the data graph during the validation process.

## 2. Getting Started with SHACL Core

In this section, we will walk you through a simple example that introduces the basics of SHACL Core.
You will learn to describe how your data should look, and how a SHACL processor checks whether your data meets that description.

### 2.1 Use Case

Imagine you have a set of entities (Alice, Bob, Calvin) and you want explain to a computer or another human that

1. there is a class called `ex:Person` that is the type of these entities
2. every instance of `ex:Person` has at most one Social Security Number (SSN), and that SSN needs to be a properly formatted text (like `123-45-6789`)
3. every instance of `ex:Person` can work for one or more companies, but those companies must be typed as a `ex:Company` in your data
4. no other properties are allowed for an `ex:Person`, other than the SSN (ex:ssn), the work affiliation (`ex:worksFor`), and the mandatory typing (`rdf:type`)

### 2.2 Our Sample Data (Data Graph)

Here is the data we want to describe and validate:

**Example: Sample Instance Data**

```
ex:Alice a ex:Person ;
    ex:ssn "987-65-432A" .                 # SSN has a typo or bad format

ex:Bob a ex:Person ;
    ex:ssn "123-45-6789", "124-35-6789" .  # Two SSNs (too many)

ex:Calvin a ex:Person ;
    ex:birthDate "1971-07-07"^^xsd:date ;  # Extra birthDate
    ex:worksFor ex:UntypedCompany .        # Untyped company
						
```

**What is wrong here?**

- **Alice** has an SSN — but it does not match the correct pattern.
- **Bob** has two SSNs, but we only allow one.
- **Calvin** works for something called `ex:UntypedCompany`,
  but that entity is not labeled as an `ex:Company`.
  Furthermore, Calvin has an `ex:birthDate`, which we do not allow in our data.

### 2.3 Writing the Shapes and Classes (Shapes Graph)

Here is a self-contained example of how to represent our domain of interest.
In SHACL terminology, this is called a shapes graph, but you can also think
of this as a *domain model* or an *ontology*.

**Example: Classes and Shapes to describe our domain of interest**

```
ex:Person
    a                    rdfs:Class ;               # or owl:Class
    rdfs:subClassOf      rdfs:Resource ;            # or owl:Thing
    rdfs:label           "Person"@en ;
    rdfs:comment         "A human being."@en ;
.
ex:PersonShape
    a                    sh:NodeShape ;
    rdfs:label           "Person shape"@en ;
    rdfs:comment         "A shape that applies to all instances of Person."@en ;
    sh:targetClass       ex:Person ;
    sh:property          ex:PersonShape-ssn ;
    sh:property          ex:PersonShape-worksFor ;
    sh:closed            true ;                     # No other properties are allowed
    sh:ignoredProperties ( rdf:type ) ;             # except for rdf:type
.
ex:PersonShape-ssn
    a                    sh:PropertyShape ;
    sh:path              ex:ssn ;                   # The values of ex:ssn are valid if:
    sh:maxCount          1 ;                        # there is at most one SSN
    sh:datatype          xsd:string ;               # the value must be a string
    sh:pattern           "^\\d{3}-\\d{2}-\\d{4}$" ; # the value must look like "123-45-6789"
    sh:name              "social security number"@en ;
    sh:description       "A person's unique identifier in the US."@en ;
.
ex:PersonShape-worksFor
    a                    sh:PropertyShape ;
    sh:path              ex:worksFor ;              # The values of ex:worksFor are valid if:
    sh:nodeKind          sh:IRI ;                   # they are IRIs (and, e.g., not literals)
    sh:class             ex:Company ;               # they are instances of Company
    sh:name              "works for"@en ;
    sh:description       "The companies that a person works for."@en ;
.
						
```

**Let us break that down:**

- `sh:targetClass ex:Person` means "apply this constraint to all people".
- The first `sh:property` definition declares that:
  - SSNs are strings (`sh:datatype xsd:string`),
  - Only one is allowed (`sh:maxCount 1`),
  - And it must follow the typical U.S. SSN format (`sh:pattern "^\d{3}-\d{2}-\d{4}$"`).
- The second `sh:property` definition declares that:
  - If someone has a `ex:worksFor` property, its value must be an IRI and point to something that's a `ex:Company`.
- `sh:closed true` means no properties beyond those listed are allowed (except any that are explicitly ignored).
- `sh:ignoredProperties ( rdf:type )` lets `rdf:type` slip through even though it's not in the allowed property list.

### 2.4 Running the Validation (Validation Report)

When we run SHACL validation on our data graph using our shapes graph, the validator checks each Person against the constraints that we wrote.

In plain English, here is what it finds:

- **Alice**: SSN does not match the expected pattern (`987-65-432A` has a letter where a digit should be).
- **Bob**: Has more than one SSN (two values found, but `sh:maxCount` says only one is allowed).
- **Calvin**:
  - Works for something (`ex:UntypedCompany`) that is not declared as a `ex:Company`.
  - Has an extra property `ex:birthDate` that is not allowed by the shape.

Here is what a SHACL validation report for this example might look like (simplified for readability):

**Example: Output produced by a SHACL validation engine**

```
[	a sh:ValidationReport ;
	sh:conforms false ;
	sh:result
	[	a sh:ValidationResult ;
		sh:resultSeverity sh:Violation ;
		sh:focusNode ex:Alice ;
		sh:resultPath ex:ssn ;
		sh:value "987-65-432A" ;
		sh:sourceConstraintComponent sh:PatternConstraintComponent ;
		sh:sourceShape ex:PersonShape-ssn ;
    	sh:resultMessage "Value does not match pattern \"^\\d{3}-\\d{2}-\\d{4}$\""@en
	] ,
	[	a sh:ValidationResult ;
		sh:resultSeverity sh:Violation ;
		sh:focusNode ex:Bob ;
		sh:resultPath ex:ssn ;
		sh:sourceConstraintComponent sh:MaxCountConstraintComponent ;
		sh:sourceShape ex:PersonShape-ssn ;
    	sh:resultMessage "More than 1 values"@en ;
	] ,
	[	a sh:ValidationResult ;
		sh:resultSeverity sh:Violation ;
		sh:focusNode ex:Calvin ;
		sh:resultPath ex:worksFor ;
		sh:value ex:UntypedCompany ;
		sh:sourceConstraintComponent sh:ClassConstraintComponent ;
		sh:sourceShape ex:PersonShape-worksFor ;
    	sh:resultMessage "Value does not have class ex:Company"@en ;
	] ,
	[	a sh:ValidationResult ;
		sh:resultSeverity sh:Violation ;
		sh:focusNode ex:Calvin ;
		sh:resultPath ex:birthDate ;
		sh:value "1971-07-07"^^xsd:date ;
		sh:sourceConstraintComponent sh:ClosedConstraintComponent ;
		sh:sourceShape sh:PersonShape ;
    	sh:resultMessage "Predicate is not allowed (closed shape)"@en ;
	]
] .
						
```

**How to read the report:**

- `sh:ValidationReport` is the overall report, with `sh:conforms false` meaning that there was at least one violation.
- Each `sh:ValidationResult` is one problem found:
  - `sh:resultSeverity` — tells you how serious the problem is. In this example, all issues are `sh:Violation` (the highest and default severity).
  - `sh:focusNode` — the data node that failed.
  - `sh:resultPath` — the property involved.
  - `sh:value` — the actual value that triggered the failure.
  - `sh:sourceConstraintComponent` — which kind of constraint was broken (max count, pattern, class, etc.).
  - `sh:sourceShape` — the shape that defined the constraint.
  - `sh:resultMessage` — a human-readable explanation.

### 2.5 Syntactic Variations of Shapes and Classes

While SHACL is primarily designed to represent shapes, it also borrows terms and concepts such as
`rdfs:Class` and `rdfs:subClassOf` from the RDF Schema namespace.
Some people prefer to keep those concepts separate, as shown in the original example above
which had separate entities for `ex:Person` and `ex:PersonShape`.
However, it is also possible to couple them more closely together, and use `sh:ShapeClass`
to declare both a class and a shape at the same time.

Furthermore, sometimes you will see property shapes declared as blank nodes instead of IRIs.
This is a more compact notation, but it means that the property shape cannot easily be referenced from
the outside; for example, if some other graph wants to reuse a node shape but deactivate a property shape.

The following Turtle example shows these two syntactic variations in action.

**Example: A more compact representation of the shapes graph**

```
ex:Person
    a                    sh:ShapeClass ;             # or rdfs:Class, sh:NodeShape
    rdfs:subClassOf      rdfs:Resource ;             # or owl:Thing
    rdfs:label           "Person"@en ;
    rdfs:comment         "A human being."@en ;
    sh:property [
        sh:path          ex:ssn ;                    # The values of ex:ssn are valid if:
        sh:maxCount      1 ;                         # there is at most one SSN
        sh:datatype      xsd:string ;                # the value must be a string
        sh:pattern       "^\\d{3}-\\d{2}-\\d{4}$" ;  # the value must look like "123-45-6789"
        sh:name          "social security number"@en ;
        sh:description   "A person's unique identifier in the US."@en ;
    ] ;
    sh:property [
        sh:path          ex:worksFor ;               # The values of ex:worksFor are valid if:
        sh:nodeKind      sh:IRI ;                    # they are IRIs (so, e.g., not literals)
        sh:class         ex:Company ;                # they are instances of Company
        sh:name          "works for"@en ;
        sh:description   "The companies that a person works for."@en ;
    ] ;
    sh:closed            true ;                      # No other properties are allowed
    sh:ignoredProperties ( rdf:type ) ;              # except for rdf:type
.
						
```

### 2.6 Introducing some SHACL Terminology

We can use the shape declarations above to introduce some of the formal terminology used by SHACL.
This may help you read the remainder of this specification.

The target for the shape `ex:PersonShape` is the set of all SHACL instances of the class `ex:Person`.
This is specified using the property `sh:targetClass`.
During the validation, these target nodes become focus nodes for the shape.
The shape `ex:PersonShape` is a node shape, which means that it applies to the focus nodes.
It declares constraints on the focus nodes, for example using the parameters `sh:closed` and `sh:ignoredProperties`.
The node shape also declares two other constraints with the property `sh:property`,
and each of these is backed by a property shape.
These property shapes declare additional constraints using parameters such as `sh:datatype` and `sh:maxCount`.

Some of the property shapes specify parameters from multiple constraint components in order to
restrict multiple aspects of the property values.
For example, in the property shape for `ex:ssn`, parameters from three constraint components are used.
The parameters of these constraint components are `sh:datatype`, `sh:pattern` and `sh:maxCount`.
For each focus node the property values of `ex:ssn` will be validated against all three components.

## 3. Shapes and Constraints

*The following introduction is non-normative.*

The following informal diagram provides an overview of some of the key classes in the SHACL vocabulary.
Each box represents a class.
The boxes under the class name list a small subset of the frequently used properties
that instances of these classes may have, together with their value types.
The arrows indicate `rdfs:subClassOf` triples.

[sh:Shape](#shapes)

[sh:targetClass](#targetClass) : rdfs:Class

[sh:targetNode](#targetNode) : any

[sh:targetObjectsOf](#targetObjectsOf) : rdf:Property

[sh:targetSubjectsOf](#targetSubjectsOf) : rdf:Property

[sh:deactivated](#deactivated) : xsd:boolean

[sh:message](#message) : text

[sh:severity](#severity) : sh:Severity

![Class Diagram Arrows](images/Class-Diagram-Arrows.svg)

[sh:NodeShape](#node-shapes)

**[Constraint parameters](#constraints)**, for example:

[sh:closed](#ClosedConstraintComponent) : xsd:boolean or sh:ByTypes

[sh:or](#OrConstraintComponent), [sh:and](#AndConstraintComponent), [sh:xone](#XoneConstraintComponent) : rdf:List

[sh:not](#NotConstraintComponent) : sh:Shape

[sh:property](#PropertyConstraintComponent) : sh:PropertyShape

[sh:PropertyShape](#property-shapes)

**[Constraint parameters](#constraints)**, for example:

[sh:minCount](#MinCountConstraintComponent), [sh:maxCount](#MaxCountConstraintComponent) : xsd:integer

[sh:minLength](#MinLengthConstraintComponent), [sh:maxLength](#MaxLengthConstraintComponent) : xsd:integer

[sh:class](#ClassConstraintComponent), [sh:datatype](#DatatypeConstraintComponent) : rdfs:Resource or rdf:List of rdfs:Resources

[sh:node](#NodeConstraintComponent) : sh:NodeShape

[sh:name](#name) : xsd:string or rdf:dirLangString or rdf:langString

[sh:description](#description) : text

[sh:defaultValue](#syntax-rule-path-defaultValue) : any

[sh:values](#syntax-rule-path-defaultValue) : any

[sh:group](#group) : sh:PropertyGroup

[sh:path](#property-shapes) : rdfs:Resource

The [Turtle serialization of the SHACL vocabulary](http://www.w3.org/ns/shacl.ttl) contains the complete SHACL vocabulary.

### 3.1 Shapes

A shape is an IRI or blank node `s`
that fulfills at least one of the following conditions in the shapes graph:

- `s` is a SHACL instance of `sh:NodeShape` or `sh:PropertyShape`.
- `s` is subject of a triple that has `sh:targetClass`, `sh:targetNode`,
  `sh:targetObjectsOf` or `sh:targetSubjectsOf` as predicate.
- `s` is subject of a triple that has a parameter as predicate.
- `s` is a value of a shape-expecting, non-list-taking parameter such as `sh:node`,
  or a member of a SHACL list that is a value of a shape-expecting and list-taking parameter such as `sh:or`.

Note that the definition above does not include all of the syntax rules of well-formed shapes.
Those are found throughout the document and summarized in Appendix [A. Summary of SHACL Syntax Rules](#syntax-rules).
For example, shapes that have literals as values for `sh:targetClass` are ill-formed.

Informally, a shape determines how to validate a focus node based on the values of properties and other characteristics of the focus node.
For example, shapes can declare the condition that a focus node be an IRI or that a focus node has a particular value for a property and also a minimum number of values for the property.

The SHACL Core language defines two types of shapes:

- shapes about the focus node itself, called node shapes
- shapes about the values of a particular property or path for the focus node, called property shapes

`sh:Shape` is the SHACL superclass of those two shape types in the SHACL vocabulary.
Its subclasses `sh:NodeShape` and `sh:PropertyShape` can be used as SHACL type of node and property shapes, respectively.

#### 3.1.1 Constraints, Parameters and Constraint Components

Shapes can declare constraints using the parameters of constraint components.

A constraint component is an IRI.
Each constraint component has one or more mandatory parameters, each of which is a property.
Each constraint component has zero or more optional parameters, each of which is a property.
The parameters of a constraint component are its mandatory parameters plus its optional parameters.

For example, the component `sh:MinCountConstraintComponent` declares the parameter `sh:minCount` to represent the restriction
that a node has at least a minimum number of values for a particular property.

For a constraint component `C` with mandatory parameters `p1`, ... `pn`,
a shape `s` in a shapes graph `SG` *declares* a constraint
that has kind `C` with mandatory parameter values `<p1,v1>`, ... `<pn,vn>`
in `SG` when `s` has `vi` as a value for `pi` in `SG`.
For constraint components with optional parameters, the constraint declaration consists of the values that the shape has for all mandatory and optional parameters of that component.

Some constraint components declare only a single parameter.
For example [`sh:ClassConstraintComponent`](#ClassConstraintComponent) has the single parameter `sh:class`.
These parameters may be used multiple times in the same shape,
and each value of such a parameter declares an individual constraint.
The interpretation of such declarations is conjunction, i.e. all constraints apply.
The following example specifies that the values of `ex:customer` have to be SHACL instances of both
`ex:Customer` and `ex:Person`.

**Example: An example of how a constraint component is used**

```
ex:InvoiceShape
    a sh:NodeShape ;
    sh:property ex:InvoiceShape-customer ;
.
ex:InvoiceShape-customer
    a sh:PropertyShape ;
    sh:path ex:customer ;
    sh:class ex:Customer ;
    sh:class ex:Person ;
.
							
```

Some constraint components such as [`sh:PatternConstraintComponent`](#PatternConstraintComponent) declare more than one parameter.
Shapes that have more than one value for any of the parameters of such components are ill-formed.

One way to bypass this syntax rule is to spread the constraints across multiple (property) shapes, as illustrated in the following example.

**Example: An example of how constraints can be spread across multiple shapes**

```
ex:MultiplePatternsShape
	a sh:NodeShape ;
	sh:property [
		sh:path ex:name ;
		sh:pattern "^Start" ;
		sh:flags "i" ;
	] ;
	sh:property [
		sh:path ex:name ;
		sh:pattern "End$" ;
	] .
							
```

Constraint components are associated with validators, which provide instructions (for example expressed via SPARQL queries)
on how the parameters are used to validate data.
Validating an RDF term against a shape involves validating the term against each constraint where the
shape has values for all mandatory parameters of the component of the constraint,
using the validators associated with the respective component.

The list of constraint components included in SHACL Core is described in [section 4](#constraints).
SHACL-SPARQL can be used to declare additional [constraint components based on SPARQL](shacl12-sparql#sparql-constraint-components).

#### 3.1.2 Focus Nodes

An RDF term that is validated against a shape using the triples from a data graph is called a focus node.

*The remainder of this section is non-normative.*

The set of focus nodes for a shape may be identified as follows:

- specified in a shape using target declarations
- specified in any constraint that references a shape
  in parameters of shape-expecting constraint parameters (e.g. `sh:node`)
- specified as explicit input to the SHACL processor for validating a specific RDF term against a shape

#### 3.1.3 Targets

Target declarations of a shape in a shapes graph are
triples with the shape as the subject and certain properties described in this document
(e.g., `sh:targetClass`) as predicates.
Furthermore, [sh:shape](#explicit-shape-target) triples can declare targets in the data graph.
Target declarations can be used to produce focus nodes for a shape.
The target of a target declaration is the set of RDF terms produced
by applying the rules described in the remainder of this section to the data graph.
The target of a shape is the union of all RDF terms produced by the individual
targets that are declared for the shape.

SHACL Core includes the following kinds of targets:

- [node targets](#targetNode)
- [class-based targets](#targetClass) (including [implicit class-based targets](#implicit-targetClass))
- [subjects-of targets](#targetSubjectsOf)
- [objects-of targets](#targetObjectsOf)
- [where targets](#targetWhere)
- [explicit shape targets](#explicit-shape-target)

*The remainder of this introduction is non-normative.*

RDF terms produced by targets are not required to exist as nodes in the data graph.
Targets of a shape are ignored whenever a focus node is provided directly as input to the validation process for that shape.
This includes the cases where the shape is a value of one of the
shape-expecting constraint parameters (such as `sh:node`) and
a focus node is determined during the validation of the corresponding constraint component (such as `sh:NodeConstraintComponent`).
In such cases, the provided focus node does not need to be in the target of the shape.

##### 3.1.3.1 Node targets (sh:targetNode)

A node target is specified using the `sh:targetNode` predicate.
Each value of `sh:targetNode` in a shape is a well-formed node expression.

If `s` is a shape in a shapes graph `SG` and `s` has
value `expr` for `sh:targetNode` in `SG`,
then the output nodes of `evalExpr(expr, data graph, s, {})` are targets
for the data graph `DG` as focus graph.

*The remainder of this section is non-normative.*

With the example data below, only `ex:Alice` is the target of the provided shape:

**Example: An example of a node target**

```
ex:PersonShape
	a sh:NodeShape ;
	sh:targetNode ex:Alice .
								
```

```
ex:Alice a ex:Person .
ex:Bob a ex:Person .
								
```

##### 3.1.3.2 Class-based Targets (sh:targetClass)

A class target is specified with the `sh:targetClass` predicate.
Each value of `sh:targetClass` in a shape is an IRI.

If `s` is a shape in a shapes graph `SG` and `s` has value `c` for
`sh:targetClass` in `SG` then the set of SHACL instances of `c` in a data graph
`DG` is a target from `DG` for `s` in `SG`.

*The remainder of this section is non-normative.*

**Example: An example of a class-based target**

```
ex:PersonShape
	a sh:NodeShape ;
	sh:targetClass ex:Person .
								
```

```
ex:Alice a ex:Person .
ex:Bob a ex:Person .
ex:NewYork a ex:Place .
								
```

In this example, only `ex:Alice` and `ex:Bob` are focus nodes.
Note that, according to the SHACL instance definition, all the `rdfs:subClassOf` declarations needed to walk the class hierarchy need to exist in the data graph.
However, the `ex:Person a rdfs:Class` triple is not required to exist in either graphs.

In the following example, the selected focus node is only `ex:Who`.

**Example: An example of a class-based target with subclassing**

```
ex:Doctor rdfs:subClassOf ex:Person .
ex:Who a ex:Doctor .
ex:House a ex:Nephrologist .
								
```

Note that the `rdfs:subClassOf` triples may be queried from the shapes graph
(see [6.3 Graph for rdfs:subClassOf Triples](#subClassOfInShapesGraph)) in which case the `rdfs:subClassOf` triple
from the example above would not be required to be in the data graph.

##### 3.1.3.3 Implicit Class Targets and sh:ShapeClass

Informally, if a shape is also declared to be a class in the shapes graph then
all SHACL instances of this class are a target for the shape.

If `s` is a SHACL instance of `sh:NodeShape` or `sh:PropertyShape`
in an RDF graph `G` and `s` is also a SHACL instance of
`rdfs:Class` in `G` and `s` is not an IRI then `s` is an ill-formed shape in `G`.

If `s` is a SHACL instance of `sh:NodeShape` or `sh:PropertyShape`
in a shapes graph `SG` and `s` is also a SHACL instance of `rdfs:Class`
in `SG` then the set of SHACL instances of `s` in a data graph `DG` is a target from `DG` for `s` in `SG`.

The SHACL namespace includes a dedicated class `sh:ShapeClass` that can serve as a syntactic shortcut for the implicit class targets pattern.

The class `sh:ShapeClass` is an `rdfs:subClassOf` of both `sh:NodeShape` and `rdfs:Class`.
If `s` is a SHACL instance of `sh:ShapeClass` in a shapes graph `SG`
then the set of SHACL instances of `s` in a data graph `DG` is a target from `DG` for `s` in `SG`.

Please keep in mind that `sh:ShapeClass` may not be understood to be a subclass of `rdfs:Class` by some SHACL-unaware implementations.
It is therefore recommended (but not required) that graphs that use `sh:ShapeClass` include an `owl:imports sh:` statement.

*The remainder of this section is non-normative.*

In the following example, `ex:Alice` is a focus node, because it is a SHACL instance of
`ex:Person` which is both a class and a shape in the shapes graph.

**Example: An example of an implicit class target**

```
ex:Person
	a rdfs:Class, sh:NodeShape .
								
```

```
ex:Alice a ex:Person .
ex:NewYork a ex:Place .
								
```

In the following variation of the example above, `ex:Person` is declared as an instance of `sh:ShapeClass`,
with the same interpretation.

**Example: An example of an implicit class target using sh:ShapeClass**

```
ex:Person
	a sh:ShapeClass .
								
```

##### 3.1.3.4 Subjects-of targets (sh:targetSubjectsOf)

A subjects-of target is specified with the predicate `sh:targetSubjectsOf`.
The values of `sh:targetSubjectsOf` in a shape are IRIs.

If `s` is a shape in a shapes graph `SG` and `s` has value
`p` for `sh:targetSubjectsOf` in `SG` then the set of nodes in a
data graph `DG` that are subjects of triples in `DG` with predicate
`p` is a target from `DG` for `s` in `SG`.

*The remainder of this section is non-normative.*

**Example: An example of a subjects-of target**

```
ex:TargetSubjectsOfExampleShape
	a sh:NodeShape ;
	sh:targetSubjectsOf ex:knows .
								
```

```
ex:Alice ex:knows ex:Bob .
ex:Bob ex:livesIn ex:NewYork .
								
```

In the example above, only `ex:Alice` is validated against the given shape,
because it is the subject of a triple that has `ex:knows` as its predicate.

##### 3.1.3.5 Objects-of targets (sh:targetObjectsOf)

An objects-of target is specified with the predicate `sh:targetObjectsOf`.
The values of `sh:targetObjectsOf` in a shape are IRIs.

If `s` is a shape in a shapes graph `SG` and `s` has value
`p` for `sh:targetObjectsOf` in `SG` then the set of nodes in a
data graph `DG` that are objects of triples in `DG` with predicate
`p` is a target from `DG` for `s` in `SG`.

*The remainder of this section is non-normative.*

**Example: An example of an objects-of target**

```
ex:TargetObjectsOfExampleShape
	a sh:NodeShape ;
	sh:targetObjectsOf ex:knows .
								
```

```
ex:Alice ex:knows ex:Bob .
ex:Bob ex:livesIn ex:NewYork .
								
```

In the example above, only `ex:Bob` is validated against the given shape,
because it is the object of a triple that has `ex:knows` as its predicate.

##### 3.1.3.6 Where Targets (sh:targetWhere)

A where target is specified with the `sh:targetWhere` predicate.
Each value of `sh:targetWhere` in a shape is a well-formed shape.

If `s` is a shape in a shapes graph `SG` and `s` has value `w` for
`sh:targetWhere` in `SG` then the set of nodes in a data graph
`DG` that conform to `w` is a target from `DG` for `s` in `SG`.

*The remainder of this section is non-normative.*

**Example: An example of a where target**

```
ex:AdultPerson
    a sh:NodeShape ;
    sh:targetWhere [
        sh:class ex:Person ;
        sh:property [
            sh:path ex:age ;
            sh:minCount 1 ;
            sh:minInclusive 18 ;
        ] ;
    ] ;
    sh:property [
        sh:path ex:votedFor ;
        sh:class ex:Person ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] .
								
```

```
ex:Alice a ex:Person .

ex:Bob a ex:Person ;
    ex:age 21 .
								
```

In this example, only `ex:Bob` is a focus node of `ex:AdultPerson`
because he conforms to the two constraints defined by the `sh:targetWhere` shape.
Based on the `sh:class` constraint, he is a SHACL instance of `ex:Person`
and his `ex:age` is 18 or greater.
However, as the `ex:AdultPerson` shape states that all adults must have one value for `ex:votedFor`,
`ex:Bob` does not conform to `ex:AdultPerson`.

Note that `sh:targetWhere` can be interpreted as a "definition" providing
necessary and sufficient conditions for a shape.
It can therefore potentially be used for "classification" tasks, e.g., to collect all nodes
that fulfill a given set of conditions.

**Note:** As a word of caution, performance of the computation of where targets can differ between implementations.
In the worst case, an engine will need to iterate over all nodes in the data graph to filter them one-by-one.

##### 3.1.3.7 Explicit shape targets (sh:shape)

An explicit shape target is specified using the `sh:shape` predicate.
Each value of `sh:shape` is an IRI.

If `s` is a shape in a shapes graph and
`n` is a node in the data graph.
If `n` has value `s` for `sh:shape` in the data graph,
then `n` is a target for `s`.

*The remainder of this section is non-normative.*

**Note:** `sh:shape` is different from `sh:targetNode`, although both can be used to
link individual nodes with shapes.
`sh:shape` points from a specific subject node to an object shape.
Furthermore, while the `sh:targetNode` triples are queried from the shapes graph,
the `sh:shape` triples are expected in the data graph.

With the example data below, only `ex:Alice` is the target of the provided shape:

**Example: An example of an explicit shape target using sh:shape**

```
ex:PersonShape
	a sh:NodeShape .
								
```

```
ex:Alice
    a ex:Person ;
    sh:shape ex:PersonShape .

ex:Bob a ex:Person .
								
```

#### 3.1.4 Declaring the Severity of a Shape or Constraint

Shapes can specify one value for the property `sh:severity` in the shapes graph.
Each value of `sh:severity` is an IRI.

In addition to declaring severities per shape, the property `sh:severity` can also be used
on a reifier for a triple where the shape is the subject and one of the parameters
of the constraint is the predicate.

Let `T` be the set of triples that represent a constraint in a shape.
A shapes graph can specify at most one value for the property `sh:severity`
in the reifiers of the triples in `T`.

A value of `sh:severity` is called a severity.
SHACL includes the IRIs listed in the table below to represent severities.
These are declared in the SHACL vocabulary as SHACL instances of `sh:Severity`.

| Severity | Description |
| --- | --- |
| `sh:Trace` | A trace message that is not a constraint violation. |
| `sh:Debug` | A debug message that is not a constraint violation. |
| `sh:Info` | A non-critical constraint violation indicating an informative message. |
| `sh:Warning` | A non-critical constraint violation indicating a warning. |
| `sh:Violation` | A constraint violation. |

*The remainder of this section is non-normative.*

The validation process handles the values of `sh:severity` according to conformance checking.
Additionally, user interface tools may use the values to categorize validation results.
The values of `sh:severity` are used by SHACL processors to populate the `sh:resultSeverity` field of
validation results, see [section on severity in validation results](#results-severity).
Any IRI can be used as a severity.

For every shape and constraint, `sh:Violation` is the default if `sh:severity` is unspecified.
The following example illustrates this.

**Example: An example of declaring severities for shapes and constraints**

```
ex:MyShape
    a sh:NodeShape ;
    sh:targetNode ex:MyInstance ;
    sh:property ex:MyShape-myProperty1 ;
    sh:property ex:MyShape-myProperty2 ;
.
ex:MyShape-myProperty1
    # Violations of sh:minCount and sh:datatype are produced as warnings
    a sh:PropertyShape ;
    sh:path ex:myProperty ;
    sh:minCount 1 ;
    sh:datatype xsd:string ;
    sh:severity sh:Warning ;
.
ex:MyShape-myProperty2
    # The default severity here is sh:Violation
    a sh:PropertyShape ;
    sh:path ex:myProperty ;
    sh:maxLength 10 ;
    sh:message "Too many characters"@en ;
    sh:message "Zu viele Zeichen"@de ;
.
							
```

```
ex:MyInstance
    ex:myProperty "http://toomanycharacters"^^xsd:anyURI .
							
```

```
[
    a sh:ValidationReport ;
    sh:conforms false ;
    sh:result [
        a sh:ValidationResult ;
        sh:resultSeverity sh:Warning ;
        sh:focusNode ex:MyInstance ;
        sh:resultPath ex:myProperty ;
        sh:value "http://toomanycharacters"^^xsd:anyURI ;
        sh:sourceConstraintComponent sh:DatatypeConstraintComponent ;
        sh:sourceShape ex:MyShape-myProperty1 ;
	] ,
	[
        a sh:ValidationResult ;
        sh:resultSeverity sh:Violation ;
        sh:focusNode ex:MyInstance ;
        sh:resultPath ex:myProperty ;
        sh:value "http://toomanycharacters"^^xsd:anyURI ;
        sh:resultMessage "Too many characters"@en ;
        sh:resultMessage "Zu viele Zeichen"@de ;
        sh:sourceConstraintComponent sh:MaxLengthConstraintComponent ;
        sh:sourceShape ex:MyShape-myProperty2 ;
	]
] .
							
```

The following example is a variation of the shapes graph above, but using reification to
specify the severity of individual constraints:

**Example: An example of declaring severities for shapes and constraints using reification**

```
ex:MyShape
    a sh:NodeShape ;
    sh:targetNode ex:MyInstance ;
    sh:property ex:MyShape-myProperty1 ;
    sh:property ex:MyShape-myProperty2 ;
.
ex:MyShape-myProperty1
    a sh:PropertyShape ;
    sh:path ex:myProperty ;
    sh:minCount 1 {| sh:severity sh:Info |} ;
    sh:datatype xsd:string {| sh:severity sh:Warning |} ;
.
ex:MyShape-myProperty2
    # The default severity here is sh:Violation
    sh:path ex:myProperty ;
    sh:maxLength 10 ;
    sh:message "Too many characters"@en ;
    sh:message "Zu viele Zeichen"@de ;
.
							
```

#### 3.1.5 Declaring Messages for a Shape or Constraint

Shapes can have values for the property `sh:message`.
The values of `sh:message` are literals with datatype
`xsd:string`, `rdf:dirLangString`, `rdf:langString`, or `rdf:HTML`.
A subject should neither have more than one value for `sh:message` with the same language tag,
nor multiple values with datatype `xsd:string`.

If a shape has at least one value for `sh:message` in the shapes graph, then
all validation results produced as a result of the shape will have exactly these messages
as their value of `sh:resultMessage`, i.e. the values will be copied from the shapes graph
into the results graph.

In addition to declaring messages per shape, the property `sh:message` can also be used
on a reifier for a triple where the shape is the subject and one of the parameters
of the constraint is the predicate.

Let `T` be the set of triples that represent a constraint in a shape.
A shapes graph can specify at most one value for the property `sh:message`
in the reifiers of the triples in `T`.

*The remainder of this section is non-normative.*

See the [section on `sh:resultMessage` in the validation results](#results-message)
on further details on how the values of `sh:resultMessage` are populated.

The example from the previous section uses this mechanism to supply the second validation result
with two messages.
The following example is a variation where the message is declared using reification.

**Example: An example of declaring messages for shapes and constraints using reification**

```
ex:MyShape
    a sh:NodeShape ;
    sh:targetNode ex:MyInstance ;
    sh:property ex:MyShape-myProperty ;
.
ex:MyShape-myProperty
    a sh:PropertyShape ;
    sh:path ex:myProperty ;
    sh:maxLength 10 {|
        sh:message "Too many characters"@en ;
        sh:message "Zu viele Zeichen"@de
    |}
.
							
```

#### 3.1.6 Deactivating Shapes and Constraints

Shapes can have at most one value for the property `sh:deactivated`.
The value of `sh:deactivated` is a node expression
that must have either `true` or `false` as the (only) output node.

Let `expr` be the value of `sh:deactivated` in a shape.
If `evalExpr(expr, data graph, focus node, {})` produces `true` as its only
output node, the shape is called deactivated.
Deactivated shapes are ignored during validation.

In addition to deactivating all constraints for a shape, it is also possible to deactivate individual constraints.
This is done using reification.

A triple that has a shape as subject,
a parameter (such as `sh:minCount`) as predicate can have at most one
reifier with a value for the property `sh:deactivated`.

Let `expr` be the value of `sh:deactivated` in a reifier on a triple
that has shape subject and a parameter as predicate.
If `evalExpr(expr, data graph, focus node, {})` produces `true` as its only
output node, the constraints that use the triple are called deactivated constraints.
Deactivated constraints are ignored during validation.

*The remainder of this section is non-normative.*

In SHACL Core, the only valid values for `sh:deactivated` are the
[constant literal node expressions](#LiteralExpression)
`true` and `false`.

Use cases of this feature include shape reuse and debugging.
In scenarios where shapes from other graphs or files are imported into a given shapes graph,
`sh:deactivated` can be set to `true` in the local shapes graph for imported shapes
to exclude shapes that do not apply in the current application context.
This makes it possible to reuse SHACL graphs developed by others even if you disagree with certain assumptions made by the original authors.
If a shape author anticipates that a shape may need to be disabled or modified by others, it is a good practice to use IRIs instead of blank nodes
for the actual shapes. For example, a property shape for the property `ex:name` at the shape `ex:PersonShape` may have the IRI `ex:PersonShape-name`.
Another typical use case of `sh:deactivated` is during the development and testing of shapes, to (temporarily) disable certain shapes.

The following example illustrates the use of `sh:deactivated` to deactivate a shape.
In cases where shapes are imported from other graphs, the `sh:deactivated true` triple would be in the importing graph.

**Example: Deactivating a property shape**

```
ex:PersonShape
	a sh:NodeShape ;
	sh:targetClass ex:Person ;
	sh:property ex:PersonShape-name .

ex:PersonShape-name
	a sh:PropertyShape ;
	sh:path ex:name ;
	sh:minCount 1 ;
	sh:deactivated true .
							
```

With the following data, no constraint violation will be reported even though the instance does not have any value for `ex:name`.

```
ex:JohnDoe a ex:Person .
							
```

The following variation uses reification to deactivate just the `sh:minCount`
constraint without affecting other constraints at the same property shape.

**Example: Deactivating individual constraints using reification**

```
ex:PersonShape
	a sh:NodeShape ;
	sh:targetClass ex:Person ;
	sh:property ex:PersonShape-name .

ex:PersonShape-name
	a sh:PropertyShape ;
	sh:path ex:name ;
	sh:minCount 1 {| sh:deactivated true |} ;
	sh:maxCount 1 .
							
```

### 3.2 Node Shapes

A node shape is a shape in the shapes graph that
is not the subject of a triple with `sh:path` as its predicate.
It is recommended, but not required, for a node shape to be declared as a SHACL instance of `sh:NodeShape`.
SHACL instances of `sh:NodeShape` cannot have a value for the property `sh:path`.

Informally, node shapes specify constraints that need to be met with respect to focus nodes.
In contrast to property shapes they primarily apply to the focus node itself, not to its property values.

### 3.3 Property Shapes

A property shape is a shape in the shapes graph
that is the subject of a triple that has `sh:path` as its predicate.
A shape has at most one value for `sh:path`.
The value of `sh:path` in a property shape is a well-formed
SHACL property path.
  
  
It is recommended, but not required, for a property shape to be declared as a SHACL instance of `sh:PropertyShape`.
SHACL instances of `sh:PropertyShape` have one value for the property `sh:path`.
  
  
A property shape has at most one value for the property `sh:values` and this value is a well-formed node expression.
A property shape has at most one value for the property `sh:defaultValue` and this value is a well-formed node expression.
A property shape can only have values for `sh:values` and/or `sh:defaultValue` when its value for `sh:path` is a [Predicate Path](#property-path-predicate).

Informally, property shapes specify constraints that need to be met with respect to nodes that can be reached from the
focus node by
(a) directly following a given property (specified as an IRI using `sh:path`),
(b) directly following any other SHACL property path (specified using `sh:path`),
(c) evaluating the node expression specified using `sh:values`, or,
(d) if no other values exist, evaluating the node expression specified using `sh:defaultValue`.

Note that support for `sh:values` and `sh:defaultValue` is not required by SHACL Core,
but is necessary for extensions such as shacl12-sparql.

Note that the definitions of well-formed property shapes and node shapes make these two sets of nodes disjoint.

The following example illustrates some syntax variations of property shapes.

**Example: Some syntax variations of property shapes**

```
ex:ExampleNodeShapeWithPropertyShapes
    a sh:NodeShape ;
    sh:property [  # Example "inline" property shape as blank node
        sh:path ex:email ;
        sh:name "e-mail"@en ;
        sh:description "We need at least one email value"@en ;
        sh:minCount 1 ;
    ] ;
    sh:property ex:ExampleNodeShapeWithPropertyShapes-knows-email ;
.
ex:ExampleNodeShapeWithPropertyShapes-knows-email
    a sh:PropertyShape ;
    sh:path (ex:knows ex:email) ;
    sh:name "Friend's e-mail"@en ;
    sh:description "We need at least one email for everyone you know"@en ;
    sh:minCount 1 ;
.
						
```

## 4. SHACL Property Paths

Property paths can be used at [`sh:path`](#property-shapes) to derive the value nodes of a property shape.

SHACL includes RDF terms to represent the following subset of SPARQL property paths:
`PredicatePath`, `InversePath`, `SequencePath`, `AlternativePath`,
`ZeroOrMorePath`, `OneOrMorePath` and `ZeroOrOnePath`.

The following sub-sections provide syntax rules of well-formed SHACL property paths
together with mapping rules to SPARQL 1.2 property paths.
These rules define the path mapping `path(p,G)` in an RDF graph `G` of an RDF term `p` that is a SHACL property path in `G`.
Two SHACL property paths are considered equivalent paths when they map to the exact same SPARQL property paths.

A node in an RDF graph is a well-formed SHACL property path `p` if it satisfies exactly one of the syntax rules in the following sub-sections.
A node `p` is not a well-formed SHACL property path if `p` is a blank node and any path mappings of `p` directly or transitively reference `p`.

The following example illustrates some valid SHACL property paths, together with their SPARQL 1.2 equivalents.

**Example: Some valid property path expressions and their SPARQL 1.2 equivalents**

```
# SPARQL Property path: ex:parent
ex:SomeClass-predicateExample
	sh:path ex:parent .

# SPARQL Property path: ^ex:parent
ex:SomeClass-inversePathExample
	sh:path [
		sh:inversePath ex:parent
	] .

# SPARQL Property path: ex:parent/ex:firstName
ex:SomeClass-sequencePathExample
	sh:path (
		ex:parent
		ex:firstName
	) .

# SPARQL Property path: rdf:type/rdfs:subClassOf*
ex:SomeClass-complexPathExample
	sh:path (
		rdf:type
		[ sh:zeroOrMorePath rdfs:subClassOf ]
	) .

# SPARQL Property path: ex:father|ex:mother
ex:SomeClass-alternativePathExample
	sh:path [
		sh:alternativePath ( ex:father ex:mother  )
	] .
					
```

### 4.1 Predicate Paths

A predicate path is an IRI.

If `p` is a predicate path, then `path(p,G)` is
a SPARQL `PredicatePath` with `p` as `iri`.

### 4.2 Sequence Paths

A sequence path is a blank node that is a SHACL list
with at least two members and each member is a well-formed SHACL property path.

If `p` is a sequence path in `G` with list members
`v1`, `v2`, ..., `vn`,
then `path(p,G)` is a SPARQL `SequencePath` of
`path(v1,G)` as `elt1`, and the results of the path mapping
of the list node of `v2` as `elt2`.

Informal note: the nodes in such a SHACL list should not have values for
other properties beside `rdf:first` and `rdf:rest`.

### 4.3 Alternative Paths

An alternative path is a blank node that is the subject of exactly one triple in `G`.
This triple has `sh:alternativePath` as predicate, `L` as object,
and `L` is a SHACL list with at least two members
and each member of `L` is a well-formed SHACL property path.

If `p` is an alternative path in `G`,
then, for the members of its SHACL list `L`:
`v1`, `v2`, ..., `vn`,
`path(p,G)` is a SPARQL `AlternativePath` with
`path(v1,G)` as `elt1` followed by an `AlternativePath`
for `v2` as `elt2`, ..., up to `path(vn,G)`.

### 4.4 Inverse Paths

An inverse path is a blank node that is the subject of exactly one triple in `G`.
This triple has `sh:inversePath` as predicate, and the object `v` is a well-formed SHACL property path.

If `p` is an inverse path in `G`, then `path(p,G)` is a
SPARQL `InversePath` with `path(v,G)` as its `elt`.

### 4.5 Zero-Or-More Paths

A zero-or-more path is a blank node that is the subject of exactly one triple in `G`.
This triple has `sh:zeroOrMorePath` as predicate, and the object `v` is a well-formed SHACL property path.

If `p` is a zero-or-more path in `G`, then `path(p,G)` is a
SPARQL `ZeroOrMorePath` with `path(v,G)` as its `elt`.

### 4.6 One-Or-More Paths

A one-or-more path is a blank node that is the subject of exactly one triple in `G`.
This triple has `sh:oneOrMorePath` as predicate, and the object `v` is a well-formed SHACL property path.

If `p` is a one-or-more path in `G`, then `path(p,G)` is a
SPARQL `OneOrMorePath` with `path(v,G)` as its `elt`.

### 4.7 Zero-Or-One Paths

A zero-or-one path is a blank node that is the subject of exactly one triple in `G`.
This triple has `sh:zeroOrOnePath` as predicate, and the object `v` is a well-formed SHACL property path.

If `p` is a zero-or-one path in `G`, then `path(p,G)` is a
SPARQL `ZeroOrOnePath` with `path(v,G)` as its `elt`.

## 5. Node Expressions

This section introduces the concept of node expressions.
SHACL Core supports node expressions in the following features:

- At [`sh:values` and `sh:defaultValue`](#property-shapes) to derive the value nodes of a property shape.
- At [`sh:targetNode`](#targetNode) to dynamically compute the targets of a shape.
- At [`sh:deactivated`](#deactivated) to deactivate certain shapes under specific conditions.

Readers who are only interested in SHACL Core can typically skip this section.
Given that Core only supports constant IRIs and literals as node expressions, the use cases of node expressions
are identical to traditional use of SHACL Core.

A node expression is a node that follows the syntax rules of exactly one node expression function.
Each node expression function has an IRI as its function name.

The evaluation of a node expression is defined as a function `evalExpr(expr, focusGraph, focusNode, scope) -> outputNodes`
where

- `expr` is a node expression in a shapes graph.
  During evaluation, the engine can access triples related to `expr` in the shapes graph.
- `focusGraph` is a graph, called the focus graph. This is the default query graph for the evaluation of the node expression.
- `focusNode` is a node, called the input focus node. This variable may have no value.
- `scope` is a map from (key) terms to individual (value) terms.
  The empty map is written as `{}`.

The result of the evaluation of a node expression is a list of nodes (possibly empty and with duplicates) called the output nodes.
The evaluation may also result in an evaluation failure.

The SHACL Core specification only exactly defines the node expression functions based on the next two subsections.
shacl12-node-expr provides more background on the general design of node expressions and includes a comprehensive
library of node expression functions.
Other specifications such as shacl12-sparql introduce additional functions, using blank nodes.
Therefore node expressions serve as an extension point of SHACL.

### 5.1 IRI Expressions

A node expression that is a IRI is called an IRI expression with the function name
`sh:IRIExpression`.

A node in an RDF graph is a well-formed IRI expression if it is an IRI.

The output nodes of an IRI expression are the list consisting of exactly the node expression itself:
  
  
`evalExpr(expr, focusGraph, focusNode, scope) -> [expr]`

### 5.2 Literal Expressions

A node expression that is a literal is called a literal expression with the function name
`sh:LiteralExpression`.

A node in an RDF graph is a well-formed literal expression if it is a literal.

The output nodes of a literal expression are the list consisting of exactly the node expression itself:
  
  
`evalExpr(expr, focusGraph, focusNode, scope) -> [expr]`

## 6. Validation and Graphs

Validation takes a data graph and a shapes graph as input and produces
a validation report containing the results of the validation.
Conformance checking is a simplified version of validation, producing a boolean result.
A system that is capable of performing validation is called a processor,
and the verb processing is sometimes used to refer to the validation process.

SHACL defines an RDF Validation Report Vocabulary that can be used by processors that produce validation reports as RDF results graphs.
This specification uses the SHACL results vocabulary for the normative definitions of the validators
associated with the constraint components.
Only SHACL implementations that can produce all of the mandatory properties of the Validation Report Vocabulary are standards-compliant.

### 6.1 Shapes Graph

A shapes graph is an RDF graph in the role of providing shapes and related information
to a SHACL validation process so that a data graph can be validated against the shapes.

The `sh:ShapesGraph` class MAY be used as an `rdf:type`
of the IRI of a graph that typically acts in the role of a shapes graph.
The graph type classes (such as `sh:DataGraph` and `sh:ShapesGraph`)
represent roles that are not mutually exclusive; a single graph MAY be typed with more than one of these classes.

The shapes graph for a given validation may be the result of combining multiple shapes graphs,
for example through `owl:imports` or `sh:shapesGraph`.
However it is constructed, the shapes graph used for validation MUST remain fixed during the validation process.
See [6.5 Validation](#validation-definition) for further details.

*The remainder of this section is non-normative.*

Shapes graphs can be reusable validation modules that can be cross-referenced with the predicate `owl:imports`.
As a pre-validation step, SHACL processors should extend the originally provided shapes graph by transitively following and importing all referenced shapes graphs
through the `owl:imports` predicate.
When resolving an imported IRI, if the retrieved graph contains a triple with the imported IRI as the object of
`owl:versionIRI`,
the processor should treat the subject of that triple as the shapes graph IRI of the imported graph
for the purpose of following further `owl:imports` statements.
Formally, processors should use the property path `^owl:versionIRI?/owl:imports` iteratively
to resolve imports, so that version IRIs can be used to import versioned shapes graphs.

In the following example, the shapes graph imports `<http://example.com/shapes/company/v2>`.
When the processor retrieves the graph at that IRI,
it finds that IRI declared as the `owl:versionIRI` of `<http://example.com/shapes/company>`.
The processor then uses `<http://example.com/shapes/company>` to identify that graph
when following further `owl:imports` statements, in this case importing `<http://example.com/shapes/base>`.

**Example: Importing a versioned shapes graph using owl:versionIRI**

```
# Shapes graph that imports a versioned shapes module
<http://example.com/shapes/myapp>
	owl:imports <http://example.com/shapes/company/v2> .

ex:PersonShape
	a sh:NodeShape ;
	sh:targetClass ex:Person ;
	sh:property [
		sh:path ex:worksFor ;
		sh:class ex:Company ;
	] .
						
```

```
# Graph retrieved from <http://example.com/shapes/company/v2>
<http://example.com/shapes/company>
	owl:versionIRI <http://example.com/shapes/company/v2> ;
	owl:imports <http://example.com/shapes/base> .

ex:CompanyShape
	a sh:NodeShape ;
	sh:targetClass ex:Company ;
	sh:property [
		sh:path ex:name ;
		sh:minCount 1 ;
		sh:datatype xsd:string ;
	] .
						
```

The resulting graph forms the immutable shapes graph for validation.

**Note:** When using `owl:versionIRI` to import versioned shapes graphs, care should be taken to
avoid importing incompatible versions. In particular, the import closure of a shapes graph
SHOULD NOT contain two graphs that are different versions of the same series, or where one
declares `owl:incompatibleWith` the other. Such a shapes graph is considered
ill-formed. See the definition of well-formed shapes graphs for details.

In addition to shape declarations, the shapes graph may contain additional information for the SHACL processor such as `sh:entailment` statements.

### 6.2 Data Graph

Any RDF graph can be a data graph.

The `sh:DataGraph` class MAY be used as an `rdf:type` of the IRI
of a graph that is typically used as a data graph.
The graph type classes (such as `sh:DataGraph` and `sh:ShapesGraph`)
represent roles that are not mutually exclusive; a single graph MAY be typed with more than one of these classes.
For example, a shapes graph MAY also play the role of a data graph
when the shapes themselves will be validated.

*The remainder of this section is non-normative.*

A data graph is one of the inputs to the SHACL processor for validation.
SHACL processors treat it as a general RDF graph and makes no assumption about its nature.
For example, it can be an in-memory graph or a named graph from an RDF dataset or a SPARQL endpoint.

SHACL can be used with RDF graphs that are obtained by any means, e.g. from the file system, HTTP requests, or RDF datasets.
SHACL makes no assumptions about whether a graph contains triples that are entailed from the graph under any RDF entailment regime.

The data graph is expected to include all the ontology axioms related to the data and especially all the
`rdfs:subClassOf` triples in order for SHACL to correctly identify class targets and validate Core SHACL constraints.

**Note:** `owl:imports` in the data graph is not enacted, in order to avoid uncontrolled increase of validation work. If you want to validate
several related ontologies, pass all of them to the SHACL processor (together or one by one), do not rely on `owl:imports` links.

**Note:** While SHACL does not enact `owl:imports` in the data graph, data graph maintainers should remain aware of applications that do rely
on `owl:imports` behavior as an import directive. In particular, some applications may be syntactically reliant on the direct
presence of `X a owl:Ontology .` such that `X owl:imports Y .` will process the `owl:imports` statement as a
directive to load `Y`. See OWL 2 Web Ontology Language Mapping
to RDF Graphs, Section 3.1.1 for further detail. Hence, when using statements of the form `X a sh:DataGraph .`, `X a owl:Ontology .`
should also be included.

### 6.3 Graph for rdfs:subClassOf Triples

Some features of SHACL (such as
[7.1.1 sh:class](#ClassConstraintComponent),
[3.1.3.2 Class-based Targets (sh:targetClass)](#targetClass), and
[3.1.3.3 Implicit Class Targets and sh:ShapeClass](#implicit-targetClass)) rely on the notion
of SHACL type to determine whether a node is a SHACL instance of a given class.
By default, this is determined by looking up `rdfs:subClassOf` and `rdf:type` triples
in the data graph.
However, this is insufficient in some cases, as `rdfs:subClassOf` triples are often stored as part
of the class and/or shape definitions and not the instance data.

SHACL processors SHOULD offer a parameter `subClassOfInShapesGraph` that, if set to `true`,
should alter the definition of SHACL Type so that the `rdfs:subClassOf` triples are queried
from the shapes graph in addition to the data graph.
The `rdf:type` triples are always expected to be in the data graph.

### 6.4 Linking data graphs to shapes graphs (sh:shapesGraph)

A data graph can include triples used to suggest one or more graphs to a SHACL processor with the predicate `sh:shapesGraph`.
Every value of `sh:shapesGraph` is an IRI representing a graph that SHOULD be included into the shapes graph used to validate the data graph.
The value of `sh:shapesGraph` may be a value of `owl:versionIRI`,
so the same strategy of resolving a shapes graph IRI from a version IRI, described for [Shapes Graphs](#shapes-graph), applies here.

In the following example, a SHACL processor SHOULD use the union of `ex:graph-shapes1` and `ex:graph-shapes2` graphs (and their `owl:imports`) as the shapes graph when validating the given graph.

**Example: Using sh:shapesGraph to link to shapes graphs from a data graph**

```
<http://example.com/myDataGraph>
    a sh:DataGraph ;
    sh:shapesGraph ex:graph-shapes1 ;
    sh:shapesGraph ex:graph-shapes2 .
						
```

### 6.5 Validation

Validation is a mapping from some input
to validation results, as defined in the following paragraphs.

Validation of a data graph against a shapes graph:
Given a data graph and a shapes graph,
the validation results are the union of results of the validation of the data graph against all
shapes in the shapes graph.

Validation of a data graph against a shape:
Given a data graph and a shape in the shapes graph,
the validation results are the union of the results of the validation of all
focus nodes that are in the target of the shape in the data graph.

Validation of a focus node against a shape:
Given a focus node in the data graph and a shape in the shapes graph,
the validation results are the union of the results of the validation of the focus node against all
constraints declared by the shape, unless the shape has been deactivated,
in which case the validation results are empty.

Validation of a focus node against a constraint:
Given a focus node in the data graph and a constraint of kind `C` in the shapes graph,
the validation results are defined by the validators of the constraint component `C`.
These validators typically take as input the focus node, the specific values of the parameters of `C`
of the constraint in the shapes graph, and the value nodes of the shape that declares the constraint.

During validation, the data graph and the shapes graph MUST remain immutable, i.e. both graphs at the end of the validation MUST be identical to the graph at the beginning of validation.
SHACL processors MUST NOT change the graphs that they use to construct the shapes graph or the data graph,
even if these graphs are part of an RDF store that allows changes to its stored graphs.
SHACL processors MAY store the graphs that they create, such as a graph containing validation results,
and this operation MAY change existing graphs in an RDF store, but not any of the graphs that were used to construct the shapes graph or the data graph.
SHACL processing is thus idempotent.

#### 6.5.1 Failures

Validation and conformance checking can result in a failure.
For example, a particular SHACL processor might allow recursive shapes but report a failure
if it detects a loop within the data.
Failures can also be reported due to resource exhaustion.
Failures are signalled through implementation-specific channels.

#### 6.5.2 Handling of Ill-formed Shapes Graphs

If the shapes graph contains ill-formed nodes, then the result of the validation process is *undefined*.
A SHACL processor SHOULD produce a failure in this case.
See also [6.7.1.4 Syntax Checking of Shapes Graph (sh:shapesGraphWellFormed)](#shapesGraphWellFormed).

#### 6.5.3 Handling of Recursive Shapes

The following properties are the so-called shape-expecting constraint parameters in SHACL Core:

- [sh:and](#AndConstraintComponent)
- [sh:not](#NotConstraintComponent)
- [sh:or](#OrConstraintComponent)
- [sh:property](#PropertyConstraintComponent)
- [sh:qualifiedValueShape](#QualifiedValueShapeConstraintComponent)
- [sh:node](#NodeConstraintComponent)
- [sh:memberShape](#MemberShapeConstraintComponent)
- [sh:reifierShape](#ReifierShapeConstraintComponent)
- [sh:someValue](#SomeValueConstraintComponent)
- [sh:xone](#XoneConstraintComponent)

The following properties are the so-called list-taking constraint parameters in SHACL Core:

- [sh:and](#AndConstraintComponent)
- [sh:in](#InConstraintComponent)
- [sh:languageIn](#LanguageInConstraintComponent)
- [sh:or](#OrConstraintComponent)
- [sh:xone](#XoneConstraintComponent)

A shape `s1` in an RDF graph `G` refers to shape `s2`
in `G` if it has `s2` as value for some non-list-taking,
shape-expecting parameter of some constraint component or `s2` as a member of
the value for some list-taking, shape-expecting parameter of some constraint component.
A shape in an RDF graph `G` is a recursive shape in `G` if it is related to
itself by the transitive closure of the refers relationship in `G`.

The validation with recursive shapes is not defined in SHACL and is left to SHACL processor implementations.
For example, SHACL processors may support recursion scenarios or produce a failure when they detect recursion.

*The remainder of this section is non-normative.*

The recursion policy above has been selected to support a large variety of implementation strategies.
By leaving recursion undefined, implementations may choose to not support recursion so that they
can issue a static set of SPARQL queries (against SPARQL end points) without having to support cycles.
The Working Group is aware that other implementations may support recursion and that some shapes graphs may
rely on these specific characteristics.
The expectation is that future work, for example in W3C Community Groups, will lead to the definition
of specific dialects of SHACL where recursion is well-defined.

### 6.6 Conformance Checking

A focus node conforms to a shape if and only if
the set of result of the validation of the focus node against the shape does not contain any validation results with a severity level of the set of disallowed levels and no failure
has been reported by it.

The set of disallowed severity levels is defined as the objects of triples with predicate
`sh:conformanceDisallows` and the validation report as subject.
If the validation report contains no such triples, `sh:Violation`, `sh:Warning`, and
`sh:Info` are set as defaults.

Conformance checking produces `true` if and only if a given focus node
conforms to a given shape, and `false` otherwise.

Note that all [shape-expecting constraint parameters](#shape-expecting-constraint-parameters) of SHACL Core
rely on conformance checking.
In these cases, the validation results used to determine the outcome of conformance checking are
separated from those of the surrounding validation process and typically do not end up in the same validation report
(except perhaps as values of [`sh:detail`](#results-detail)).

#### 6.6.1 Conforms To Shapes Graph (sh:conformsToShapesGraph)

A data graph MAY use the property `sh:conformsToShapesGraph` to indicate that it conforms to a given shapes graph.
The value is an IRI identifying the shapes graph.
This property has `rdfs:domain sh:DataGraph` and `rdfs:range sh:ShapesGraph`.

**Note:** See the [Conforms To Shapes Graph](../shacl12-profiling/#prop-conformstoshapesgraph) section of SHACL 1.2 Profiling for further details on the use of this property.

### 6.7 Validation Report

The validation report is the result of the validation process that reports the conformance and the set of all validation results.
The validation report is described with the SHACL Validation Report Vocabulary as defined in this section.
This vocabulary defines the RDF properties to represent structural information that may provide guidance on how to identify or fix violations in the data graph.

SHACL-compliant processors MUST be capable of returning a validation report with all required validation results
described in this specification.
SHACL-compliant processors MAY support optional arguments that make it possible to limit the number of returned results.
This flexibility is for example needed in some large-scale dataset validation use cases.

The following graph represents an example of a validation report for the validation of a data graph that conforms to a shapes graph.

**Example: Example of a validation report for a conforming data graph**

```
[ 	a sh:ValidationReport ;
	sh:conforms true ;
	sh:conformanceDisallows sh:Violation ;
	sh:result [
		a sh:ValidationResult ;
		sh:resultSeverity sh:Warning ;
		sh:focusNode ex:Bob ;
		sh:resultPath ex:age ;
		sh:value "twenty two"@en ;
		sh:resultMessage "ex:age expects a literal of datatype xsd:integer."@en ;
		sh:sourceConstraintComponent sh:DatatypeConstraintComponent ;
		sh:sourceShape ex:PersonShape-age ;
	]
] .
						
```

The following graph represents an example of a validation report for the validation of a data graph that does not conform to a shapes graph.
Note that the specific value of `sh:resultMessage` is not mandated by SHACL and considered implementation-specific.

**Example: Example of a validation report for a non-conforming data graph**

```
[	a sh:ValidationReport ;
	sh:conforms false ;
	sh:conformanceDisallows sh:Violation ;
	sh:result [
		a sh:ValidationResult ;
		sh:resultSeverity sh:Violation ;
		sh:focusNode ex:Bob ;
		sh:resultPath ex:age ;
		sh:value "twenty two"@en ;
		sh:resultMessage "ex:age expects a literal of datatype xsd:integer."@en ;
		sh:sourceConstraintComponent sh:DatatypeConstraintComponent ;
		sh:sourceShape ex:PersonShape-age ;
	]
] .
						
```

#### 6.7.1 Validation Report (sh:ValidationReport)

The result of a validation process is an RDF graph with exactly one SHACL instance of `sh:ValidationReport`.
The RDF graph MAY contain additional provenance metadata.
In particular, a validation report MAY use [`sh:usedDataGraph`](#usedDataGraph) to identify the data graph that was validated,
[`sh:usedShapesGraph`](#usedShapesGraph) to identify the shapes graph that was used,
and [`sh:usedConfiguration`](#usedConfiguration) to link to a `sh:ProcessorConfiguration` instance
describing the processor's state and settings at the time of validation.
Together, these properties allow a report to be self-contained with respect to the context in which it was produced.

**Note:** See the [Validation Report](../shacl12-profiling/#cls-validationreport) section of SHACL 1.2 Profiling for further details and examples of self-contained validation reports.

##### 6.7.1.1 Conforms (sh:conforms)

Each SHACL instance of `sh:ValidationReport` in the results graph has exactly one value for the property `sh:conforms` and the value is of datatype `xsd:boolean`.
It represents the outcome of the conformance checking.

##### 6.7.1.2 Conformance-Disallow Set (`sh:conformanceDisallows`)

Each SHACL instance of `sh:ValidationReport` in the results graph MAY have one or more values
for the property `sh:conformanceDisallows`. All values of `sh:conformanceDisallows` MUST be IRIs.

All values combined define the set of disallowed
severity levels. Presence of any `sh:ValidationResult` with a severity level in the set of
disallowed severity levels MUST result in a `sh:conforms` value
of `false` on the associated `sh:ValidationReport` instance.

If no values are present in the results graph for the property
`sh:conformanceDisallows`, then a default set MUST be used, comprised of
`sh:Violation`, `sh:Warning`, and `sh:Info`.

The conformance-disallow set is defined by the validation engine.
A validation engine MAY provide mechanisms to customize this set.

##### 6.7.1.3 Result (sh:result)

For every validation result that is produced by a validation process
(except those mentioned in the context of [conformance checking](#conformance-nested)),
the SHACL instance of `sh:ValidationReport` in the results graph has a value for the property `sh:result`.
Each value of `sh:result` is a SHACL instance of the class `sh:ValidationResult`.

##### 6.7.1.4 Syntax Checking of Shapes Graph (sh:shapesGraphWellFormed)

SHACL validation engines are not strictly required to check whether the shapes graph is well-formed.
Implementations that do perform such checks (e.g., when the shapes graph is installed in the system,
or before or during the validation) SHOULD use the property `sh:shapesGraphWellFormed` to inform the
consumer of the validation report about this fact.
If a SHACL instance of `sh:ValidationReport` in the results graph has `true` as the value
for `sh:shapesGraphWellFormed` then the processor was certain that the shapes graph that was used for the
validation process is well-formed.

##### 6.7.1.5 Used Data Graph (sh:usedDataGraph)

A SHACL instance of `sh:ValidationReport` in the results graph MAY have a value for the property `sh:usedDataGraph`.
The value is an IRI that identifies the data graph that was validated by the processor to produce the report.
The version IRI of a data graph MAY also be used as a value for this property.

##### 6.7.1.6 Used Shapes Graph (sh:usedShapesGraph)

A SHACL instance of `sh:ValidationReport` in the results graph MAY have a value for the property `sh:usedShapesGraph`.
The value is an IRI that identifies the shapes graph that was used by the processor during the validation process.
The version IRI of a shapes graph MAY also be used as a value for this property.

##### 6.7.1.7 Used Configuration (sh:usedConfiguration)

A SHACL instance of `sh:ValidationReport` in the results graph MAY have a value for the property `sh:usedConfiguration`.
The value is an instance of `sh:ProcessorConfiguration` describing the state and settings of the
processor that produced the report.
SHACL processors MUST NOT alter their validation behavior based on the contents of a `sh:ProcessorConfiguration` instance.

##### 6.7.1.8 Processor Configuration (sh:ProcessorConfiguration)

`sh:ProcessorConfiguration` is the class of processor configurations.
Instances of this class describe the state and settings of a SHACL processor at the time it produced a validation report.
The properties of `sh:ProcessorConfiguration` instances are not defined by this specification.

**Note:** Implementations are free to define whatever properties they need on instances of this class, such as processor name, processor version,
maximum recursion depth, or other runtime parameters.

#### 6.7.2 Validation Result (sh:ValidationResult)

SHACL defines `sh:ValidationResult` as a subclass of `sh:AbstractResult` to report individual SHACL validation results.
SHACL implementations may use other SHACL subclasses of `sh:AbstractResult`, for example,
to report successfully completed constraint checks or accumulated results.

All the properties described in the remaining sub-sections of this section can be specified in a `sh:ValidationResult`.
The properties `sh:focusNode`, `sh:resultSeverity` and `sh:sourceConstraintComponent`
are the only properties that are mandatory for all validation results.

##### 6.7.2.1 Focus node (sh:focusNode)

Each validation result has exactly one value for the property `sh:focusNode`
that is equal to the focus node that has caused the result.
This is the focus node that was validated when the validation result was produced.

##### 6.7.2.2 Path (sh:resultPath)

Validation results may have a value for the property `sh:resultPath` pointing at a well-formed SHACL property path.
For results produced by a property shape, this SHACL property path is equivalent to the value of `sh:path` of the shape,
unless stated otherwise. 
If the `sh:path` `p` is a blank node, then the `sh:resultPath` is a deep copy of `p` in the results graph.

##### 6.7.2.3 Value (sh:value)

Validation results may include, as a value of the property `sh:value`,
at most one RDF term that has caused the result.
The textual definitions of the validators of the SHACL Core components specify how this
value is constructed - often they are the value nodes that have violated a constraint.

##### 6.7.2.4 Source (sh:sourceShape)

Validation results may include, as the only value of the property `sh:sourceShape`,
the shape that the given `sh:focusNode` was validated against.

##### 6.7.2.5 Constraint Component (sh:sourceConstraintComponent)

Validation results have exactly one value for the property `sh:sourceConstraintComponent`
and this value is the IRI of the constraint component that caused the result.
For example, results produced due to a violation of a constraint based on a value of `sh:minCount`
would have the source constraint component `sh:MinCountConstraintComponent`.

##### 6.7.2.6 Details (sh:detail)

The property `sh:detail` may link a (parent) result with one or more SHACL instances of
`sh:AbstractResult` that can provide further details about the cause of the (parent) result.
Depending on the capabilities of the SHACL processor, this may for example include violations of
constraints that have been evaluated as part of conformance checking via `sh:node`.

##### 6.7.2.7 Message (sh:resultMessage)

Validation results may have values for the property `sh:resultMessage`,
for example to communicate additional textual details to humans.
While `sh:resultMessage` may have multiple values, there should not be two values with the same language tag.
These values are produced by a validation engine based on the values of `sh:message` of the constraints
in the shapes graph, see [Declaring Messages for a Shape](#message).
Messages declared using reification have precedence over those declared at the surrounding shape.
In cases where a constraint does not have any values for `sh:message` in the shapes graph the
SHACL processor MAY automatically generate other values for `sh:resultMessage`.

##### 6.7.2.8 Severity (sh:resultSeverity)

Each validation result has exactly one value for the property `sh:resultSeverity`, and this value is an IRI.
The value is determined by the following rules (in order):

1. the value of [`sh:severity`](#severity) at a reifier of any of the triples containing the parameters of the constraint that caused the result
2. the value of [`sh:severity`](#severity) of the shape in the shapes graph that caused the result
3. defaulting to `sh:Violation` if no `sh:severity` has been specified for the shape or constraint.

### 6.8 Value Nodes

The validators of most constraint components use the concept of value nodes, which is defined by the following two sub-sections.

#### 6.8.1 Value Nodes of Node Shapes

For node shapes the value nodes are the individual focus nodes, forming a set with exactly one member.

#### 6.8.2 Value Nodes of Property Shapes

For property shapes with a value for `sh:path` `p` the
set of value nodes is produced by the following steps:

1. Add all nodes in the data graph that can be reached from the focus node with the path mapping of `p`.
2. If `e` is the value of `sh:values` at the property shape,
   then add the output nodes of `evalExpr(e, data graph, focus node, {})`.
3. If the set is still empty and `d` is the value of `sh:defaultValue` at the property shape,
   then add the output nodes of `evalExpr(d, data graph, focus node, {})`.

## 7. Core Constraint Components

This section defines the built-in SHACL Core constraint components that MUST be supported by all SHACL Core processors.
The definition of each constraint component contains its IRI as well as a table of its parameters.
Unless stated otherwise, all these parameters are mandatory parameters.
Shapes that violate any of the syntax rules enumerated in those parameter tables are ill-formed.

Each constraint component also includes a textual definition, which describes the validator associated with the component.
These textual definitions refer to the values of the parameters in the constraint by variables of the form
`$paramName` where `paramName` is the part of the parameter's IRI after the `sh:` namespace.
For example, the textual definition of `sh:ClassConstraintComponent` refers to the value of
`sh:class` using the variable `$class`.
In SHACL Core, the term parameter value means the value of a parameter,
i.e. the object of the triple in the shapes graph where the subject is the shape
and the predicate is the parameter (such as `sh:class`).

At the time of writing, the intent of the WG is to define a dialect of SHACL outside of SHACL Core in which the term
parameter value also allows node expressions.
Note that not all constraint components use the term parameter value but instead refer to the term value.
For example, the values of `sh:node` cannot ever be node expressions, because this would complicate
the handling of blank nodes.
TODO: Add link to Node Expression spec in case it's ready, or clarify the sentences above otherwise.

Note that these validators define the *only* validation results that are being produced by the component.
Furthermore, the validators always produce *new* result nodes, i.e. when the textual definition states that
"...there is a validation result..." then this refers to a distinct new node in a results graph.

*The remainder of this section is non-normative.*

The choice of constraint components that were included into the SHACL Core was made based on
the requirements collected by the shacl-ucr document.
Special attention was paid to the balance between trying to cover as many common use cases as possible
and keeping the size of the Core language manageable.
Not all use cases can be expressed by the Core language alone.
Instead, SHACL-SPARQL provides an extension mechanism, described in the second part of this specification.
It is expected that additional reusable libraries of constraint components will be maintained by third parties.

Unless stated otherwise, the Core constraint components can be used both in property shapes and node shapes.
Some constraint parameters have syntax rules attached to them that would make node shapes that use these parameters ill-formed.
Examples of this include `sh:minCount` which is only supported for property shapes.

### 7.1 Value Type Constraint Components

The constraint components in this section have in common that they can be used to restrict the type of value nodes.
Note that it is possible to represent multiple value type alternatives using [sh:or](#OrConstraintComponent).

#### 7.1.1 sh:class

The condition specified by `sh:class` is that each value node is a SHACL instance of the given type(s).

Constraint Component IRI: `sh:ClassConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:class` | The type of all value nodes. The values of `sh:class` in a shape are either IRIs or blank nodes that are well-formed SHACL lists where all members are IRIs. |

Let `$class` be a parameter value for `sh:class`.
Let `classes` be a set of IRIs so that
when `$class` is an IRI then the set only consists of exactly that IRI,
and when `$class` is a blank node SHACL list then the set consists of
exactly the members of the list.  
  
For each value node
that is either a literal, or a non-literal that is not a SHACL instance of any of the `classes` in the data graph,
there is a validation result with the value node as `sh:value`.

*The remainder of this section is non-normative.*

Note that multiple values for `sh:class` are interpreted as a conjunction,
i.e., the values need to be SHACL instances of all of them.
Use lists for union semantics.

**Example: Example of the use of sh:class with multiple values**

```
ex:ClassExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Bob, ex:Alice, ex:Carol ;
    sh:property ex:ClassExampleShape-address ;
.
ex:ClassExampleShape-address
    a sh:PropertyShape ;
    sh:path ex:address ;
    sh:class ex:PostalAddress ;
.
							
```

```
ex:Alice a ex:Person .
ex:Bob ex:address [ a ex:PostalAddress ; ex:city ex:Berlin ] .
ex:Carol ex:address [ ex:city ex:Cairo ] .
							
```

The following example illustrates the list-based syntax for `sh:class`,
meaning that the values of the property `ex:pet` must be either cats or dogs.

**Example: Example of the use of sh:class with a list value**

```
ex:ClassListExampleShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:ClassListExampleShape-pet ;
.
ex:ClassListExampleShape-pet
    a sh:PropertyShape ;
    sh:path ex:pet ;
    sh:class ( ex:Cat ex:Dog ) ;
.
							
```

```
ex:Tessie a ex:Cat .
ex:Rusty a ex:Dog .
ex:Fluffy a ex:Unicorn .

ex:Alice a ex:Person ; ex:pet ex:Tessie, ex:Rusty .
ex:Bob a ex:Person ; ex:pet ex:Fluffy .
							
```

#### 7.1.2 sh:datatype

`sh:datatype` specifies a condition to be satisfied with regards to the datatype of each value node.

Constraint Component IRI: `sh:DatatypeConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:datatype` | The allowed datatype(s) of all value nodes (e.g., `xsd:integer`). A shape has at most one value for `sh:datatype`. The value of `sh:datatype` in a shape is either an IRI or a blank node that is a well-formed SHACL list where all members are IRIs. |

Let `$datatype` be a parameter value for `sh:datatype`.
Let `datatypes` be a set of IRIs so that
when `$datatype` is an IRI then the set only consists of exactly that IRI,
and when `$datatype` is a blank node SHACL list then the set consists of
exactly the members of the list.  
  
For each value node
that is not a literal, or is a literal with a datatype that matches none of the `datatypes`,
there is a validation result with the value node as `sh:value`.  
  
The datatype of a literal is determined following the datatype function of SPARQL 1.2.
A literal matches a datatype if the literal's datatype has the same IRI
and, for the datatypes supported by SPARQL 1.2, is not an ill-typed literal.

*The remainder of this section is non-normative.*

The values of `sh:datatype` are typically datatypes, such as `xsd:string`.

**Example: Shape with an IRI as sh:datatype property constraint**

```
ex:DatatypeExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Alice, ex:Bob, ex:Carol ;
    sh:property ex:DatatypeExampleShape-age ;
.
ex:DatatypeExampleShape-age
    a sh:PropertyShape ;
    sh:path ex:age ;
    sh:datatype xsd:integer ;
.
							
```

```
ex:Alice ex:age "23"^^xsd:integer .
ex:Bob ex:age "twenty two" .
ex:Carol ex:age "23"^^xsd:int .
							
```

The following example illustrates the list-based syntax, meaning that all values of
`rdfs:label` must be either `xsd:string` or `rdf:langString`.

**Example: Shape with a list of IRIs as sh:datatype property constraint**

```
ex:TextExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Estonia, ex:GreatBritain ;
    sh:property ex:TextExampleShape-label ;
.
ex:TextExampleShape-label
    a sh:PropertyShape ;
    sh:path rdfs:label ;
    sh:datatype ( xsd:string rdf:langString ) ;
.
							
```

```
ex:Estonia rdfs:label "Estonia", "Estland"@de .
ex:GreatBritain rdfs:label "Great Britain", "<b>Great</b> Britain"^^rdf:HTML .
							
```

#### 7.1.3 sh:nodeKind

`sh:nodeKind` specifies a condition to be satisfied by the RDF node kind of each value node.

Constraint Component IRI: `sh:NodeKindConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:nodeKind` | The node kind (IRI, blank node, literal, triple term, or combination of these) of all value nodes. A shape has at most one value for `sh:nodeKind`. The value of `sh:nodeKind` in a shape is either an IRI or a blank node that is a well-formed SHACL list where all members are IRIs.     If the values of `sh:nodeKind` are IRIs, then the values of `sh:nodeKind` in a shape are one of the following seven instances of the class `sh:NodeKind`: `sh:BlankNode`, `sh:IRI`, `sh:Literal` `sh:BlankNodeOrIRI`, `sh:BlankNodeOrLiteral`, `sh:IRIOrLiteral`, and `sh:TripleTerm`.    If the values of `sh:nodeKind` are well-formed SHACL lists, then members of those lists in a shape are one of the following four instances of the class `sh:NodeKind`: `sh:BlankNode`, `sh:IRI`, `sh:Literal`, and `sh:TripleTerm`. |

Let `$nodeKind` be a parameter value for `sh:nodeKind`.
Let `$nodeKinds` be a set of IRIs so that
when `$nodeKind` is an IRI then the set only consists of exactly that IRI,
and when `$nodeKind` is a blank node SHACL list then the set consists of
exactly the members of the list.  
  
For each value node
that matches none of the `$nodeKinds`,
there is a validation result with the value node as `sh:value`.
Any IRI matches only `sh:IRI`, `sh:BlankNodeOrIRI` and `sh:IRIOrLiteral`.
Any blank node matches only `sh:BlankNode`, `sh:BlankNodeOrIRI` and `sh:BlankNodeOrLiteral`.
Any literal matches only `sh:Literal`, `sh:BlankNodeOrLiteral` and `sh:IRIOrLiteral`.
Any triple term matches only `sh:TripleTerm`.

*The remainder of this section is non-normative.*

The following example states that all values of `ex:knows` need to be IRIs, at any subject.

**Example: Example of the use of sh:nodeKind with an IRI value**

```
ex:NodeKindExampleShape
	a sh:NodeShape ;
	sh:targetObjectsOf ex:knows ;
	sh:nodeKind sh:IRI .
							
```

```
ex:Bob ex:knows ex:Alice .
ex:Alice ex:knows "Bob" .
							
```

The following example illustrates the list-based syntax, meaning that all values of `ex:knows`
need to be IRIs or blank nodes, at any subject.

**Example: Example of the use of sh:nodeKind with a list of IRIs as value**

```
ex:NodeKindExampleShape
    a sh:NodeShape ;
    sh:targetObjectsOf ex:knows ;
    sh:nodeKind ( sh:BlankNode sh:IRI ) .
							
```

```
ex:Bob ex:knows ex:Alice .
ex:Bob ex:knows _:john .
ex:Alice ex:knows "Bob" .
							
```

### 7.2 Cardinality Constraint Components

The following constraint components represent restrictions on the number of value nodes for the given focus node.

#### 7.2.1 sh:minCount

`sh:minCount` specifies the minimum number of value nodes that satisfy the condition.
If the minimum cardinality value is 0 then this constraint is always satisfied and so may be omitted.

Constraint Component IRI: `sh:MinCountConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:minCount` | The minimum cardinality. Node shapes cannot have any value for `sh:minCount`. A property shape has at most one value for `sh:minCount`. The values of `sh:minCount` in a property shape are literals with datatype `xsd:integer`. |

Let `$minCount` be a parameter value for `sh:minCount`.
If the number of value nodes is less than `$minCount`,
there is a validation result.

*The remainder of this section is non-normative.*

**Example: Example of the use of sh:minCount**

```
ex:MinCountExampleShape
    a sh:PropertyShape ;
    sh:targetNode ex:Alice, ex:Bob ;
    sh:path ex:name ;
    sh:minCount 1 .
							
```

```
ex:Alice ex:name "Alice" .
ex:Bob ex:givenName "Bob"@en .
							
```

#### 7.2.2 sh:maxCount

`sh:maxCount` specifies the maximum number of value nodes that satisfy the condition.

Constraint Component IRI: `sh:MaxCountConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:maxCount` | The maximum cardinality. Node shapes cannot have any value for `sh:maxCount`. A property shape has at most one value for `sh:maxCount`. The values of `sh:maxCount` in a property shape are literals with datatype `xsd:integer`. |

Let `$maxCount` be a parameter value for `sh:maxCount`.
If the number of value nodes is greater than `$maxCount`,
there is a validation result.

*The remainder of this section is non-normative.*

**Example: Example of the use of sh:maxCount**

```
ex:MaxCountExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Bob ;
    sh:property ex:MaxCountExampleShape-birthDate ;
.
ex:MaxCountExampleShape-birthDate
    a sh:PropertyShape ;
    sh:path ex:birthDate ;
    sh:maxCount 1 ;
.
							
```

```
ex:Bob ex:birthDate "May 5th 1990" .
							
```

### 7.3 Value Range Constraint Components

The following constraint components specify value range conditions to be satisfied by value nodes that are comparable
via operators such as `<`, `<=`, `>` and `>=`.
The following example illustrates a typical use case of these constraint components.

**Example: Example of a numeric range constraint**

```
ex:NumericRangeExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Bob, ex:Alice, ex:Ted ;
    sh:property ex:NumericRangeExampleShape-age ;
.
ex:NumericRangeExampleShape-age
    a sh:PropertyShape ;
    sh:path ex:age ;
    sh:minInclusive 0 ;
    sh:maxInclusive 150 ;
.
						
```

```
ex:Bob ex:age 23 .
ex:Alice ex:age 220 .
ex:Ted ex:age "twenty one"@en .
						
```

#### 7.3.1 sh:minExclusive

Constraint Component IRI: `sh:MinExclusiveConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:minExclusive` | The minimum exclusive value. The values of `sh:minExclusive` in a shape are literals. A shape has at most one value for `sh:minExclusive`. |

Let `$minExclusive` be a parameter value for `sh:minExclusive`.
For each value node `v`
where the SPARQL expression `$minExclusive < v` does not return `true`,
there is a validation result with `v` as `sh:value`.

*The remainder of this section is non-normative.*

There is a validation result if the value node cannot be compared to the specified range,
for example when someone compares a string with an integer.

#### 7.3.2 sh:minInclusive

Constraint Component IRI: `sh:MinInclusiveConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:minInclusive` | The minimum inclusive value. The values of `sh:minInclusive` in a shape are literals. A shape has at most one value for `sh:minInclusive`. |

Let `$minInclusive` be a parameter value for `sh:minInclusive`.
For each value node `v`
where the SPARQL expression `$minInclusive <= v` does not return `true`,
there is a validation result with `v` as `sh:value`.

#### 7.3.3 sh:maxExclusive

Constraint Component IRI: `sh:MaxExclusiveConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:maxExclusive` | The maximum exclusive value. The values of `sh:maxExclusive` in a shape are literals. A shape has at most one value for `sh:maxExclusive`. |

Let `$maxExclusive` be a parameter value for `sh:maxExclusive`.
For each value node `v`
where the SPARQL expression `$maxExclusive > v` does not return `true`,
there is a validation result with `v` as `sh:value`.

#### 7.3.4 sh:maxInclusive

Constraint Component IRI: `sh:MaxInclusiveConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:maxInclusive` | The maximum inclusive value. The values of `sh:maxInclusive` in a shape are literals. A shape has at most one value for `sh:maxInclusive`. |

Let `$maxInclusive` be a parameter value for `sh:maxInclusive`.
For each value node `v`
where the SPARQL expression `$maxInclusive >= v` does not return `true`,
there is a validation result with `v` as `sh:value`.

### 7.4 String-based Constraint Components

The constraint components in this section have in common that they specify conditions
on the string representation of value nodes.

#### 7.4.1 sh:minLength

`sh:minLength` specifies the minimum string length of each value node that satisfies the condition.
This can be applied to any literals and IRIs, but not to blank nodes.

Constraint Component IRI: `sh:MinLengthConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:minLength` | The minimum length. The values of `sh:minLength` in a shape are literals with datatype `xsd:integer`. A shape has at most one value for `sh:minLength`. |

Let `$minLength` be a parameter value for `sh:minLength`.
For each value node `v`
where the length (as defined by the SPARQL STRLEN function)
of the string representation of `v` (as defined by the SPARQL str function)
is less than `$minLength`, or where `v` is a blank node,
there is a validation result with `v` as `sh:value`.

*The remainder of this section is non-normative.*

Note that if the value of `sh:minLength` is 0 then there is no restriction on the
string length but the constraint is still violated if the value node is a blank node.

#### 7.4.2 sh:maxLength

`sh:maxLength` specifies the maximum string length of each value node that satisfies the condition.
This can be applied to any literals and IRIs, but not to blank nodes.

Constraint Component IRI: `sh:MaxLengthConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:maxLength` | The maximum length. The values of `sh:maxLength` in a shape are literals with datatype `xsd:integer`. A shape has at most one value for `sh:maxLength`. |

Let `$maxLength` be a parameter value for `sh:maxLength`.
For each value node `v`
where the length (as defined by the SPARQL STRLEN function)
of the string representation of `v` (as defined by the SPARQL str function)
is greater than `$maxLength`, or where `v` is a blank node,
there is a validation result with `v` as `sh:value`.

*The remainder of this section is non-normative.*

**Example: Example of the use of sh:minLength and sh:maxLength**

```
ex:PasswordExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Bob, ex:Alice ;
    sh:property ex:PasswordExampleShape-password ;
.
ex:PasswordExampleShape-password
    a sh:PropertyShape ;
    sh:path ex:password ;
    sh:minLength 8 ;
    sh:maxLength 10 ;
.
							
```

```
ex:Bob ex:password "123456789" .
ex:Alice ex:password "1234567890ABC" .
							
```

#### 7.4.3 sh:pattern

`sh:pattern` specifies a regular expression that each value node matches to satisfy the condition.

Constraint Component IRI: `sh:PatternConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:pattern` | A regular expression that all value nodes need to match. The values of `sh:pattern` in a shape are literals with datatype `xsd:string`. The values of `sh:pattern` in a shape are valid pattern arguments for the SPARQL REGEX function. |
| `sh:flags` | An optional string of flags, interpreted as in SPARQL 1.2 REGEX. The values of `sh:flags` in a shape are literals with datatype `xsd:string`. |

Let `$pattern` be a parameter value for `sh:pattern`.
Let `$flags` be a parameter value for `sh:flags`.
For each value node
that is a blank node or
where the string representation (as defined by the SPARQL str function)
does not match the regular expression `$pattern` (as defined by the SPARQL REGEX function),
there is a validation result with the value node as `sh:value`.
If `$flags` has a value then the matching MUST follow the definition of the 3-argument variant of the SPARQL REGEX function, using `$flags` as third argument.

*The remainder of this section is non-normative.*

**Example: Example of the use of sh:pattern and sh:flags**

```
ex:PatternExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Bob, ex:Alice, ex:Carol ;
    sh:property ex:PatternExampleShape-bCode ;
.
ex:PatternExampleShape-bCode
    a sh:PropertyShape ;
    sh:path ex:bCode ;
    sh:pattern "^B" ;    # starts with 'B'
    sh:flags "i" ;       # Ignore case
.
							
```

```
ex:Bob ex:bCode "b101" .
ex:Alice ex:bCode "B102" .
ex:Carol ex:bCode "C103" .
							
```

#### 7.4.4 sh:singleLine

This feature is "at risk" pending a WG resolution on this (and similar) convenience features.
The WG is not sure yet where to draw the lines between features that should go into Core versus some other document.
Originally discussed as [Issue 177](https://github.com/w3c/data-shapes/issues/177).

When set to `true`, `sh:singleLine` specifies that the value nodes must not contain line breaks.
In addition to constraint validation, this information can be exploited by user interface builders to select between (single-lined) text fields and (multi-lined) text areas.

Constraint Component IRI: `sh:SingleLineConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:singleLine` | `true` to activate this constraint. The values of `sh:singleLine` in a shape are literals with datatype `xsd:boolean`. A shape has at most one value for `sh:singleLine`. |

Let `$singleLine` be a parameter value for `sh:singleLine`.
If `$singleLine` is `true`, then, for each value node that is a literal where the lexical form matches the
regular expression (as defined by the SPARQL REGEX function) `[\f\r\n\v]`, there is a validation result.

*The remainder of this section is non-normative.*

**Example: Example of the use of sh:singleLine**

In this example, the valid target nodes of the shape can only contain single-lined values for `rdfs:label`.
The values of `rdfs:comment` are explicitly allowed to contain line breaks, indicating to form builders that
those values should be edited in a multi-line (text area) input widget.

```
ex:SingleLineExampleShape
    a sh:NodeShape ;
    sh:property ex:SingleLineExampleShape-label ;
    sh:property ex:SingleLineExampleShape-comment ;
.
ex:SingleLineExampleShape-label
    a sh:PropertyShape ;
    sh:path rdfs:label ;
    sh:datatype xsd:string ;
    sh:singleLine true ;
.
ex:SingleLineExampleShape-comment
    a sh:PropertyShape ;
    sh:path rdfs:comment ;
    sh:datatype ( xsd:string rdf:dirLangString rdf:langString ) ;
    sh:singleLine false ;
.
							
```

#### 7.4.5 sh:languageIn

The condition specified by `sh:languageIn` is that the allowed language tags for each value node are limited by a given list of language tags.

Constraint Component IRI: `sh:LanguageInConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:languageIn` | A list of basic language ranges as per BCP47. Each value of `sh:languageIn` in a shape is a SHACL list. Each member of such a list is a literal with datatype `xsd:string`. A shape has at most one value for `sh:languageIn`. |

Let `$languageIn` be a value of `sh:languageIn`.
For each value node
that is either not a literal or that does not have a language tag
matching any of the basic language ranges that are the members of `$languageIn`
following the filtering schema defined by the SPARQL langMatches function,
there is a validation result with the value node as `sh:value`.

*The remainder of this section is non-normative.*

The following example shape states that all values of `ex:prefLabel`
can be either in English or Māori.

**Example: Example of the use of sh:languageIn**

```
ex:NewZealandLanguagesShape
    a sh:NodeShape ;
    sh:targetNode ex:Mountain, ex:Berg ;
    sh:property ex:NewZealandLanguagesShape-prefLabel ;
.
ex:NewZealandLanguagesShape-prefLabel
    a sh:PropertyShape ;
    sh:path ex:prefLabel ;
    sh:languageIn ( "en" "mi" ) ;
.
							
```

From the example instances, `ex:Berg` will lead to constraint violations for all
of its labels.

```
ex:Mountain
    ex:prefLabel "Mountain"@en ;
    ex:prefLabel "Hill"@en-nz ;
    ex:prefLabel "Maunga"@mi .

ex:Berg
    ex:prefLabel "Berg" ;
    ex:prefLabel "Berg"@de ;
    ex:prefLabel ex:BergLabel .
							
```

#### 7.4.6 sh:uniqueLang

The property `sh:uniqueLang` is set to `true` to specify that no pair of value nodes may use the same language tag, including considering the text direction, if present.

Constraint Component IRI: `sh:UniqueLangConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:uniqueLang` | `true` to activate this constraint. The values of `sh:uniqueLang` in a shape are literals with datatype `xsd:boolean`. A property shape has at most one value for `sh:uniqueLang`. Node shapes cannot have any value for `sh:uniqueLang`. |

Let `$uniqueLang` be a parameter value for `sh:uniqueLang`.
If `$uniqueLang` is `true`
then for each non-empty language tag that is used by at least two value nodes,
there is a validation result.
For value nodes of datatype `rdf:dirLangString`,
the base direction is included in the uniqueness condition,
e.g., `"1"@ar--rtl` and `"1"@ar-ltr` are different,
as is the pair `"1"@ar--rtl` and `"1"@ar`.

*The remainder of this section is non-normative.*

**Example: Example of the use of sh:uniqueLang**

```
ex:UniqueLangExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Alice, ex:Bob ;
    sh:property ex:UniqueLangExampleShape-label ;
.
ex:UniqueLangExampleShape-label
    a sh:PropertyShape ;
    sh:path ex:label ;
    sh:uniqueLang true ;
.
							
```

```
ex:Alice
    ex:label "Alice" ;
    ex:label "Alice"@en ;
    ex:label "Alice"@fr .

ex:Bob
    ex:label "Bob"@en ;
    ex:label "Bobby"@en .
							
```

### 7.5 List Constraint Components

The constraint components in this section apply to value nodes that are [SHACL lists](#syntax-rule-SHACL-list).
They specify conditions on the structure, length, and members of SHACL lists.

#### 7.5.1 sh:memberShape

`sh:memberShape` specifies that all members of [SHACL list](#syntax-rule-SHACL-list) value nodes must conform to the given node shape.

Constraint Component IRI: `sh:MemberShapeConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:memberShape` | The shape that all members of the [SHACL list](#syntax-rule-SHACL-list) must conform to. The values of `sh:memberShape` must be well-formed node shapes. |

Let `$memberShape` be a parameter value for `sh:memberShape`.
Each value node `v` must be a [SHACL list](#syntax-rule-SHACL-list) - if `v` is not a SHACL list there is a validation result.
If any member `m` of the [SHACL list](#syntax-rule-SHACL-list) `v` does not conform to `$memberShape`, there is a validation result.

*The remainder of this section is non-normative.*

Each member `m` of a value node `v` that does not conform to the `$memberShape` should be reported as a separate `sh:detail` in the validation result for `v`.
If `v` is not a valid [SHACL list](#syntax-rule-SHACL-list), this should be reported as a top-level validation result and validation of individual members should not be attempted.

Examples of how to generate `sh:detail`s in validation results can be found in the test cases for `sh:memberShape` in the SHACL test suite: [memberShape-001.ttl](../shacl12-test-suite/tests/core/node/memberShape-001.ttl).

In the following example, all values of the property `ex:speakerOrder` must be SHACL lists with members that are IRIs.

**Example: Example of the use of sh:memberShape**

```
ex:AgendaShape
    a sh:NodeShape ;
    sh:targetClass ex:Agenda ;
    sh:property ex:AgendaShape-speakerOrder ;
.
ex:AgendaShape-speakerOrder
    a sh:PropertyShape ;
    sh:path ex:speakerOrder ;
    sh:memberShape [
        sh:nodeKind sh:IRI ;
    ] ;
.
							
```

```
ex:agenda1 a ex:Agenda ;
    ex:speakerOrder ( ex:Alice ex:Bob ex:Charlie ) .

ex:agenda2 a ex:Agenda ;
    ex:speakerOrder ( ex:Alice ex:Bob "Charlie" ) .
							
```

#### 7.5.2 sh:minListLength

`sh:minListLength` specifies the minimum number of members that [SHACL list](#syntax-rule-SHACL-list) value nodes must have.

Constraint Component IRI: `sh:MinListLengthConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:minListLength` | The minimum number of members in the [SHACL list](#syntax-rule-SHACL-list). The values of `sh:minListLength` in a shape are literals with datatype `xsd:integer`. The values of `sh:minListLength` in a shape are integers greater than or equal to 0. |

Let `$minListLength` be a parameter value for `sh:minListLength`.
Each value node `v` must be a [SHACL list](#syntax-rule-SHACL-list) - if `v` is not a SHACL list there is a validation result.
If the number of members in a list `v` is less than `$minListLength`,
there is a validation result.

*The remainder of this section is non-normative.*

In the following example, all values of the property `ex:skills` must be SHACL lists with at least 1 member.
Additional test cases for `sh:minListLength` can be found in the SHACL test suite: [minListLength-001.ttl](../shacl12-test-suite/tests/core/node/minListLength-001.ttl).

**Example: Example of the use of sh:minListLength**

```
ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:PersonShape-skills ;
.
ex:PersonShape-skills
    a sh:PropertyShape ;
    sh:path ex:skills ;
    sh:minListLength 1 ;
.
							
```

```
ex:person1 a ex:Person ;
    ex:skills ( "programming" "design" ) .

ex:person2 a ex:Person ;
    ex:skills () .
							
```

#### 7.5.3 sh:maxListLength

`sh:maxListLength` specifies the maximum number of members that [SHACL list](#syntax-rule-SHACL-list) value nodes must have.

Constraint Component IRI: `sh:MaxListLengthConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:maxListLength` | The maximum number of members in the [SHACL list](#syntax-rule-SHACL-list). The values of `sh:maxListLength` in a shape are literals with datatype `xsd:integer`. The values of `sh:maxListLength` in a shape are integers greater than or equal to 0. |

Let `$maxListLength` be a parameter value for `sh:maxListLength`.
Each value node `v` must be a [SHACL list](#syntax-rule-SHACL-list) - if `v` is not a SHACL list there is a validation result.
If the number of members in the list `v` is greater than `$maxListLength`,
there is a validation result.

*The remainder of this section is non-normative.*

In the following example, all values of the property `ex:hobbies` must be SHACL lists with at most 2 members.
Additional test cases for `sh:maxListLength` can be found in the SHACL test suite: [maxListLength-001.ttl](../shacl12-test-suite/tests/core/node/maxListLength-001.ttl).

**Example: Example of the use of sh:maxListLength**

```
ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:PersonShape-hobbies ;
.
ex:PersonShape-hobbies
    a sh:PropertyShape ;
    sh:path ex:hobbies ;
    sh:maxListLength 2 ;
.
							
```

```
ex:person1 a ex:Person ;
    ex:hobbies ( "reading" "writing" ) .

ex:person2 a ex:Person ;
    ex:hobbies ( "reading" "writing" "swimming" ) .
							
```

#### 7.5.4 sh:uniqueMembers

`sh:uniqueMembers` specifies whether [SHACL list](#syntax-rule-SHACL-list) value nodes must have unique members.

Constraint Component IRI: `sh:UniqueMembersConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:uniqueMembers` | A boolean that specifies whether the members of the [SHACL list](#syntax-rule-SHACL-list) must be unique. The values of `sh:uniqueMembers` in a shape are literals with datatype `xsd:boolean`. |

Let `$uniqueMembers` be a parameter value for `sh:uniqueMembers`.
Each value node `v` must be a [SHACL list](#syntax-rule-SHACL-list) - if `v` is not a SHACL list there is a validation result.
If `$uniqueMembers` is `true` and the list `v` has duplicate members,
there is a validation result.

*The remainder of this section is non-normative.*

Each duplicate member `m` of a list `v` should be reported as a separate `sh:detail` in the validation result for `v`. If the list `v` is not a valid [SHACL list](#syntax-rule-SHACL-list), this should be reported as a top-level validation result and validation of unique membership should not be attempted.

Examples of how to generate `sh:detail`s in validation results can be found in the test cases for `sh:uniqueMembers` in the SHACL test suite: [uniqueMembers-001.ttl](../shacl12-test-suite/tests/core/node/uniqueMembers-001.ttl).

In the following example, all values of the property `ex:preferences` must be SHACL lists with members that have unique values within each SHACL list.

**Example: Example of the use of sh:uniqueMembers**

```
ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:PersonShape-preferences ;
.
ex:PersonShape-preferences
    a sh:PropertyShape ;
    sh:path ex:preferences ;
    sh:uniqueMembers true ;
.
							
```

```
ex:person1 a ex:Person ;
    ex:preferences ( "coffee" "tea" ) .

ex:person2 a ex:Person ;
    ex:preferences ( "coffee" "tea" "coffee" "tea" "tea" ) .
							
```

### 7.6 Property Pair Constraint Components

The constraint components in this section specify conditions on the sets of value nodes in relation to other properties or property paths.
These constraint components can only be used by property shapes.

#### 7.6.1 sh:equals

`sh:equals` specifies the condition that the set of all value nodes is equal to the set of nodes
that can be reached from the focus node via the SHACL property path that is specified using `sh:equals`.

Constraint Component IRI: `sh:EqualsConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:equals` | The property path to compare with. The values of `sh:equals` in a shape are well-formed SHACL property paths. |

Let `$equals` be a value of `sh:equals`, and `$path`
be the SHACL property path represented by `$equals` in the shapes graph.
Let `$otherNodes` be the set of nodes that can be reached from the focus node via `$path`.
For each value node
that does not exist in `$otherNodes`,
there is a validation result with the value node as `sh:value`.
For each node in `$otherNodes`
that is not one of the value nodes,
there is a validation result with the value as `sh:value`.

*The remainder of this section is non-normative.*

The following example illustrates the use of `sh:equals` in a shape to specify
that certain focus nodes need to have the same set of values for `ex:firstName` and `ex:givenName`.

**Example: Shape with sh:equals between two IRI properties**

```
ex:EqualExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Bob ;
    sh:property ex:EqualExampleShape-firstName ;
.
ex:EqualExampleShape-firstName
    a sh:PropertyShape ;
    sh:path ex:firstName ;
    sh:equals ex:givenName ;
.
							
```

```
ex:Bob
    ex:firstName "Bob" ;
    ex:givenName "Bob" .
							
```

The following example shows that SHACL property paths can be used both as values
of `sh:path` and `sh:equals`.

**Example: Shape with sh:equals between two paths**

```
ex:Person
    a sh:ShapeClass ;
    sh:property ex:Person-spouseShouldBeTattoo .

ex:Person-spouseShouldBeTattoo
    a sh:PropertyShape ;
    sh:severity sh:Warning ;
    sh:path ( ex:spouse ex:name ) ;
    sh:equals ( ex:tattoo ex:text ) .
							
```

```
ex:Alice
    a ex:Person ;
    ex:name "Alice" .

ex:Bob
    a ex:Person ;
    ex:name "Bob" ;
    ex:spouse ex:Alice ;
    ex:tattoo ex:BobsTattoo .

ex:BobsTattoo
    ex:drawing "heart" ;
    ex:text "Alice" .
							
```

In this example, warnings would be reported if Bob had
a spouse with a different name than his tattoo, or vice versa.
No warning would be produced if Bob has neither spouse nor tattoo, or
has both and their names and texts match exactly the same set of nodes.

#### 7.6.2 sh:disjoint

`sh:disjoint` specifies the condition that the set of value nodes
is disjoint with the set of nodes that can be reached from the focus node
via the SHACL property path that is the value of `sh:disjoint`.

Constraint Component IRI: `sh:DisjointConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:disjoint` | The property path to compare the values with. The values of `sh:disjoint` in a shape are well-formed SHACL property paths. |

Let `$disjoint` be a parameter value of `sh:disjoint`, and `$path`
be the SHACL property path represented by `$disjoint` in the shapes graph.
Let `$otherNodes` be the set of nodes that can be reached from the focus node via `$path`.
For each value node that is also in `$otherNodes`,
there is a validation result with the value node as `sh:value`.

*The remainder of this section is non-normative.*

The following example illustrates the use of `sh:disjoint` in a shape to specify
that certain focus nodes cannot share any values for `ex:prefLabel` and `ex:altLabel`.

**Example: Shape with sh:disjoint between two IRI properties**

```
ex:DisjointExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:USA, ex:Germany ;
    sh:property ex:DisjointExampleShape ;
.
ex:DisjointExampleShape
    a sh:PropertyShape ;
    sh:path ex:prefLabel ;
    sh:disjoint ex:altLabel ;
.
							
```

```
ex:USA
    ex:prefLabel "USA" ;
    ex:altLabel "United States" .

ex:Germany
    ex:prefLabel "Germany" ;
    ex:altLabel "Germany" .
							
```

#### 7.6.3 sh:subsetOf

`sh:subsetOf` specifies the condition that all value nodes must *also* be reachable
from the focus node via the SHACL property path that is specified using `sh:subsetOf`.

Constraint Component IRI: `sh:SubsetOfConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:subsetOf` | The property path to compare with. The values of `sh:subsetOf` in a shape are well-formed SHACL property paths. |

Let `$subsetOf` be a value of `sh:subsetOf`, and `$path`
be the SHACL property path represented by `$subsetOf` in the shapes graph.
Let `$otherNodes` be the set of nodes that can be reached from the focus node via `$path`.
For each value node that does not exist in `$otherNodes`,
there is a validation result with the value node as `sh:value`.

*The remainder of this section is non-normative.*

The following example illustrates the use of `sh:subsetOf` in a shape to specify
that the favorite child of a person must be among the actual children.

**Example: Shape with sh:subsetOf between two IRI properties**

```
ex:ParentShape
    a sh:NodeShape ;
    sh:targetNode ex:Bob ;
    sh:property ex:ParentShape-favoriteChild ;
.
ex:ParentShape-favoriteChild
    a sh:PropertyShape ;
    sh:path ex:favoriteChild ;
    sh:subsetOf ex:child ;
.
							
```

```
ex:Bob
    ex:child "Calvin" ;
    ex:child "Donald" ;
    ex:favoriteChild "Calvin" .
							
```

#### 7.6.4 sh:lessThan

`sh:lessThan` specifies the condition that each value node is smaller than all
the nodes that can be reached from the focus node via the SHACL property path
that is the value of `sh:lessThan`.

Constraint Component IRI: `sh:LessThanConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:lessThan` | The property path to compare the values with. The values of `sh:lessThan` in a shape are well-formed SHACL property paths. Node shapes cannot have any value for `sh:lessThan`. |

Let `$lessThan` be a value of `sh:lessThan`, and `$path`
be the SHACL property path represented by `$lessThan` in the shapes graph.
Let `$otherNodes` be the set of nodes that can be reached from the focus node via `$path`.
For each pair of a value node and a member of `$otherNodes`
where the first value is not less than the second value (based on SPARQL's `<` operator)
or where the two values cannot be compared,
there is a validation result with the value node as `sh:value`.

*The remainder of this section is non-normative.*

The following example illustrates the use of `sh:lessThan` in a shape to specify
that all values of `ex:startDate` are "before" the values of `ex:endDate`.

**Example: Shape with sh:lessThan between two IRI properties**

```
ex:LessThanExampleShape
    a sh:NodeShape ;
    sh:property ex:LessThanExampleShape-startDate ;
.
ex:LessThanExampleShape-startDate
    a sh:PropertyShape ;
    sh:path ex:startDate ;
    sh:lessThan ex:endDate ;
.
							
```

#### 7.6.5 sh:lessThanOrEquals

`sh:lessThanOrEquals` specifies the condition that each value node is smaller than or equal to
all the nodes that can be reached from the focus node via the SHACL property path
that is the value of `sh:lessThanOrEquals`.

Constraint Component IRI: `sh:LessThanOrEqualsConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:lessThanOrEquals` | The property path to compare the values with. The values of `sh:lessThanOrEquals` in a shape are well-formed SHACL property paths. Node shapes cannot have any value for `sh:lessThanOrEquals`. |

Let `$lessThanOrEquals` be a value of `sh:lessThanOrEquals`, and `$path`
be the SHACL property path represented by `$lessThanOrEquals` in the shapes graph.
Let `$otherNodes` be the set of nodes that can be reached from the focus node via `$path`.
For each pair of a value node and a member of `$otherNodes`
where the first value is not less than or equal to the second value (based on SPARQL's `<=` operator)
or where the two values cannot be compared,
there is a validation result with the value node as `sh:value`.

### 7.7 Logical Constraint Components

The constraint components in this section implement the common logical operators
*and*, *or* and *not*, as well as a variation of *exclusive or*.

#### 7.7.1 sh:not

`sh:not` specifies the condition that each value node cannot conform to a given shape.
This is comparable to negation and the logical "not" operator.

Constraint Component IRI: `sh:NotConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:not` | The shape to negate. The values of `sh:not` in a shape must be well-formed shapes. |

Let `$not` be a value of `sh:not`.
For each value node `v`:
A failure MUST be reported if the conformance checking of `v` against
the shape `$not` produces a failure.
Otherwise, if `v` conforms to the shape `$not`,
there is validation result with `v` as `sh:value`.

*The remainder of this section is non-normative.*

The following example illustrates the use of `sh:not` in a shape to specify the condition
that certain focus nodes cannot have any value of `ex:property`.

**Example: Shape with sh:not to specify that certain focus nodes cannot have any value of a property**

```
ex:NotExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:InvalidInstance1 ;
    sh:not [
        a sh:PropertyShape ;
        sh:path ex:property ;
        sh:minCount 1 ;
    ] .
							
```

```
ex:InvalidInstance1 ex:property "Some value" .
							
```

#### 7.7.2 sh:and

`sh:and` specifies the condition that each value node conforms to all provided shapes.
This is comparable to conjunction and the logical "and" operator.

Constraint Component IRI: `sh:AndConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:and` | A SHACL list of shapes to validate the value nodes against. Each value of `sh:and` in a shape is a SHACL list. Each member of such list must be a well-formed shape. |

Let `$and` be a value of `sh:and`.
For each value node `v`:
A failure MUST be produced if the conformance checking of `v` against any of the members of `$and` produces a failure.
Otherwise, if `v` does not conform to each member of `$and`,
there is a validation result with `v` as `sh:value`.

*The remainder of this section is non-normative.*

Note that although `sh:and` has a SHACL list of shapes as its value,
the order of those shapes does not impact the validation results.
For implementations that use shortcut evaluation semantics, the order may impact the efficiency of validation.
It is recommended to put earlier in the list constraints that are easier to evaluate, or are more likely to fail.

The following example illustrates the use of `sh:and` in a shape to specify the condition
that certain focus nodes have exactly one value of `ex:property`.
This is achieved via the conjunction of a separate named shape (`ex:SuperShape`) which specifies
the minimum count, and a property shape that additionally specifies the maximum count.
As shown here, `sh:and` can be used to implement a specialization mechanism between shapes.

**Example: Example of the use of sh:and**

```
ex:SuperShape
    a sh:NodeShape ;
    sh:property [
        sh:path ex:property ;
        sh:minCount 1 ;
    ] ;
.
ex:ExampleAndShape
    a sh:NodeShape ;
    sh:targetNode ex:ValidInstance, ex:InvalidInstance ;
    sh:and (
        ex:SuperShape
        [
            sh:path ex:property ;
            sh:maxCount 1 ;
        ]
    ) ;
.
							
```

```
ex:ValidInstance
    ex:property "One" .

# Invalid: more than one property
ex:InvalidInstance
    ex:property "One" ;
    ex:property "Two" .
							
```

#### 7.7.3 sh:or

`sh:or` specifies the condition that each value node conforms to at least one of the provided shapes.
This is comparable to disjunction and the logical "or" operator.

Constraint Component IRI: `sh:OrConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:or` | A SHACL list of shapes to validate the value nodes against. Each value of `sh:or` in a shape is a SHACL list. Each member of such list must be a well-formed shape. |

Let `$or` be a value of `sh:or`.
For each value node `v`:
A failure MUST be produced if the conformance checking of `v` against any of the members produces a failure.
Otherwise, if `v` conforms to none of the members of `$or`
there is a validation result with `v` as `sh:value`.

*The remainder of this section is non-normative.*

Note that although `sh:or` has a SHACL list of shapes as its value,
the order of those shapes does not impact the validation results.
For implementations that use shortcut evaluation semantics, the order may impact the efficiency of validation.
It is recommended to put earlier in the list constraints that are easier to evaluate, or are more likely to succeed.

The following example illustrates the use of `sh:or` in a shape to specify the condition
that certain focus nodes have at least one value of `ex:firstName`
or at least one value of `ex:givenName`.

**Example: Example of the use of sh:or**

```
ex:OrConstraintExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Bob ;
    sh:or (
        [
            sh:path ex:firstName ;
            sh:minCount 1 ;
        ]
        [
            sh:path ex:givenName ;
            sh:minCount 1 ;
        ]
    ) ;
.
							
```

```
ex:Bob ex:firstName "Robert" .
							
```

The next example shows how `sh:or` can be used in a property shape to state that the values of
the given property `ex:address` may be either literals with datatype `xsd:string`
or SHACL instances of the class `ex:Address`.

**Example: Example of the use of sh:or in a property shape**

```
ex:PersonAddressShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:PersonAddressShape-address ;
.
ex:PersonAddressShape-address
    a sh:PropertyShape ;
    sh:path ex:address ;
    sh:or (
        [
            sh:datatype xsd:string ;
        ]
        [
            sh:class ex:Address ;
        ]
    )
.
							
```

```
ex:Bob ex:address "123 Prinzengasse, Vaduz, Liechtenstein" .
							
```

Note that all constraints in SHACL get ANDed for execution. Consider the following example:

**Example: Example of the use of sh:or to specify a condition that is a conjunction of disjunctions**

```
ex:shapeRoot a sh:NodeShape;
    sh:or
        (ex:shapeA ex:shapeB),
        (ex:shapeC ex:shapeD).
							
```

The correct interpretation is (`shapeA` OR `shapeB`) AND (`shapeC` OR `shapeD`).
The target nodes need to conform to `shapeA` or `shapeB`, and then also `shapeC` or `shapeD`.

#### 7.7.4 sh:xone

`sh:xone` specifies the condition that each value node conforms to *exactly one* of the provided shapes.

Constraint Component IRI: `sh:XoneConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:xone` | A SHACL list of shapes to validate the value nodes against. Each value of `sh:xone` in a shape is a SHACL list. Each member of such list *MUST* be a well-formed shape. Each such list *SHOULD* have at least one member. |

Let `$xone` be a value of `sh:xone`.
For each value node `v`
let `N` be the number of the shapes that are members of `$xone`
where `v` conforms to the shape.
A failure MUST be produced if the conformance checking of `v` against any of the members produces a failure.
Otherwise, if `N` is not exactly `1`,
there is a validation result with `v` as `sh:value`.

*The remainder of this section is non-normative.*

Note that although `sh:xone` has a SHACL list of shapes as its value,
the order of those shapes does not impact the validation results.

The following example illustrates the use of `sh:xone` in a shape to specify the condition
that certain focus nodes must either have a value for `ex:fullName` or values for
`ex:firstName` and `ex:lastName`, but not both.

**Example: Example of the use of sh:xone to specify a condition that is a conjunction of disjunctions**

```
ex:XoneConstraintExampleShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:xone (
        [
            sh:property [
                sh:path ex:fullName ;
                sh:minCount 1 ;
            ]
        ]
        [
            sh:property [
                sh:path ex:firstName ;
                sh:minCount 1 ;
            ] ;
            sh:property [
                sh:path ex:lastName ;
                sh:minCount 1 ;
            ]
        ]
    ) ;
.
							
```

```
ex:Bob a ex:Person ;
    ex:firstName "Robert" ;
    ex:lastName "Coin" .

ex:Carla a ex:Person ;
    ex:fullName "Carla Miller" .

ex:Dory a ex:Person ;
    ex:firstName "Dory" ;
    ex:lastName "Dunce" ;
    ex:fullName "Dory Dunce" .
							
```

### 7.8 Shape-based Constraint Components

The constraint components in this section can be used to specify complex conditions
by validating the value nodes against certain shapes.

#### 7.8.1 sh:node

`sh:node` specifies the condition that each value node conforms to the given node shape.

Constraint Component IRI: `sh:NodeConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:node` | The node shape that all value nodes need to conform to. The values of `sh:node` in a shape must be well-formed node shapes. |

Let `$node` be a value of `sh:node`.
For each value node `v`:
A failure MUST be produced if the conformance checking of `v` against `$node` produces a failure.
Otherwise, if `v` does not conform to `$node`,
there is a validation result with `v` as `sh:value`.

*The remainder of this section is non-normative.*

The following example illustrates the use of `sh:node` in property shapes.
All values of the property `ex:address` must fulfill the
constraints expressed by the shape `ex:AddressShape`.

**Example: Example of sh:node in a property shape**

```
ex:AddressShape
    a sh:NodeShape ;
    sh:property ex:AddressShape-postalCode ;
.
ex:AddressShape-postalCode
    a sh:PropertyShape ;
    sh:path ex:postalCode ;
    sh:datatype xsd:string ;
    sh:maxCount 1 ;
.

ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:PersonShape-address ;
.
ex:PersonShape-address
    a sh:PropertyShape ;
    sh:path ex:address ;
    sh:minCount 1 ;
    sh:node ex:AddressShape ;
.
							
```

```
ex:Bob a ex:Person ;
    ex:address ex:BobsAddress .

ex:BobsAddress
    ex:postalCode "1234" .

ex:Reto a ex:Person ;
    ex:address ex:RetosAddress .

ex:RetosAddress
    ex:postalCode 5678 .
							
```

```
[
    a sh:ValidationReport ;
    sh:conforms false ;
    sh:result [
        a sh:ValidationResult ;
        sh:resultSeverity sh:Violation ;
        sh:focusNode ex:Reto ;
        sh:resultPath ex:address ;
        sh:value ex:RetosAddress ;
        sh:resultMessage "Value does not conform to shape ex:AddressShape."@en ;
        sh:sourceConstraintComponent sh:NodeConstraintComponent ;
        sh:sourceShape ex:PersonShape-address ;
    ] ;
] .
							
```

The following example illustrates the use of `sh:node` in node shapes.

**Example: Example of sh:node in node shapes**

```
ex:PostalCodeShape
    a sh:NodeShape ;
    rdfs:label "Postal code"@en ;
    rdfs:comment "General constraints for postal codes around the world."@en ;
    sh:datatype xsd:string ;
    sh:minLength 3 ;
.
ex:AustralianPostalCode
    a sh:NodeShape ;
    rdfs:label "Postal code (Australia)"@en ;
    rdfs:comment "Constraints that specialize those from ex:PostalCodeShape."@en ;
    sh:intent "Australian postal codes consist of 4 digits."@en ;
    sh:pattern "^\\d{4}$" ;
    sh:minLength 4 ;
    sh:maxLength 4 ;
    sh:node ex:PostalCodeShape ;
.
ex:USZipCode
    a sh:NodeShape ;
    rdfs:label "Zip code (USA)"@en ;
    rdfs:comment "Constraints that specialize those from ex:PostalCodeShape."@en ;
    sh:intent "US zip codes are either 5 digits or 5 plus 4 with a dash in between."@en ;
    sh:pattern "^\\d{5}(-\\d{4})?$" ;
    sh:minLength 5 ;
    sh:maxLength 10 ;
    sh:node ex:PostalCodeShape ;
.
							
```

This example defines a general base shape for postal codes and two specializations
for specific countries.
The base constraints such as `sh:datatype xsd:string` and `sh:minLength 3`
apply to all postal codes.
The property `sh:node` is used to link the narrower shapes to the broader shape,
similar to how `rdfs:subClassOf` is used to link a subclass with a superclass.

See [6.5.3 Handling of Recursive Shapes](#shapes-recursion) on the handling of recursive shapes in SHACL.

#### 7.8.2 sh:property

`sh:property` can be used to specify that each value node has a given property shape.

Constraint Component IRI: `sh:PropertyConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:property` | A property shape that all value nodes need to have. Each value of `sh:property` in a shape must be a well-formed property shape. |

Let `$property` be a value of `sh:property`.
For each value node `v`:
A failure MUST be produced if the validation of `v` as focus node against the property shape `$property` produces a failure.
Otherwise, the validation results are the results of validating `v` as focus node against the property shape `$property`.

*The remainder of this section is non-normative.*

Note that there is an important difference between `sh:property` and `sh:node`:
If a value node is violating the constraint, then there is only a single validation result for `sh:node` for this value node,
with `sh:NodeConstraintComponent` as its `sh:sourceConstraintComponent`.
On the other hand side, there may be any number of validation results for `sh:property`, and these
will have the individual constraint components of the constraints in the property shape as their values of `sh:sourceConstraintComponent`.

Like with all other validation results, each time a property shape is reached via `sh:property`,
a validation engine MUST produce *fresh* validation result nodes.
This includes cases where the same focus node is validated against the same property shape
although it is reached via different paths in the shapes graph.

#### 7.8.3 sh:someValue

`sh:someValue` specifies the condition that at least one value node conforms to the given shape.

Constraint Component IRI: `sh:SomeValueConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:someValue` | The shape that at least one of the value nodes needs to conform to. The values of `sh:someValue` in a shape must be well-formed shapes. |

Let `$someValue` be a value of `sh:someValue`.
A failure MUST be produced if the conformance checking of any value node against
`$someValue` produces a failure, unless at least one of the value nodes conforms to `$someValue`.
Otherwise, if none of the value nodes conforms to `$someValue`,
there is a validation result.

*The remainder of this section is non-normative.*

Note that implementations may stop processing value nodes once one of the value nodes has conformed.
Since the order of nodes in the set of value nodes is undefined, there is no guarantee that any node is
reached that would cause a failure.
Therefore, to make processing predictable, failures are silently ignored unless all value nodes have been visited without success.

In the following example, any nodes that conform to `ex:DuckFarmerShape` need to have at least one value
for `ex:tendsAnimal` that is a SHACL instance of `ex:Duck`.

**Example: Example of the use of sh:someValue**

```
ex:DuckFarmerShape
    a sh:NodeShape ;
    sh:property ex:DuckFarmerShape-tendsAnimal ;
.
ex:DuckFarmerShape-tendsAnimal
    a sh:PropertyShape ;
    sh:path ex:tendsAnimal ;
    sh:someValue [
        sh:class ex:Duck ;
    ] ;
.
							
```

`sh:someValue` can be regarded as syntactic sugar for a combination of
`sh:qualifiedValueShape` and `sh:qualifiedMinCount 1`.

Also note that `sh:someValue` mostly makes sense when used in property shapes.
In node shapes, `sh:someValue` is equivalent to using `sh:node` or `sh:property`.

#### 7.8.4 sh:qualifiedValueShape, sh:qualifiedMinCount, sh:qualifiedMaxCount

`sh:qualifiedValueShape` specifies the condition that a specified number of value nodes conforms to the given shape.
Each `sh:qualifiedValueShape` can have: one value for `sh:qualifiedMinCount`, one value for `sh:qualifiedMaxCount` or, one value for each, at the same subject.

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:qualifiedValueShape` | The shape that the specified number of value nodes needs to conform to. The values of `sh:qualifiedValueShape` in a shape must be well-formed shapes. Node shapes cannot have any value for `sh:qualifiedValueShape`. This is a mandatory parameter of `sh:QualifiedMinCountConstraintComponent` and `sh:QualifiedMaxCountConstraintComponent`. |
| `sh:qualifiedValueShapesDisjoint` | This is an optional parameter of `sh:QualifiedMinCountConstraintComponent` and `sh:QualifiedMaxCountConstraintComponent`. If set to `true` then (for the counting) the value nodes must not conform to any of the sibling shapes. The values of `sh:qualifiedValueShapesDisjoint` in a shape are literals with datatype `xsd:boolean`. |
| `sh:qualifiedMinCount` | The minimum number of value nodes that conform to the shape. The values of `sh:qualifiedMinCount` in a shape are literals with datatype `xsd:integer`. This is a mandatory parameter of `sh:QualifiedMinCountConstraintComponent`. |
| `sh:qualifiedMaxCount` | The maximum number of value nodes that can conform to the shape. The values of `sh:qualifiedMaxCount` in a shape are literals with datatype `xsd:integer`. This is a mandatory parameter of `sh:QualifiedMaxCountConstraintComponent`. |

Let `Q` be a shape in shapes graph `G` that declares a qualified cardinality constraint
(by having values for `sh:qualifiedValueShape` and at least one of `sh:qualifiedMinCount` or `sh:qualifiedMaxCount`).
Let `ps` be the set of shapes in `G` that have `Q` as a value of `sh:property`.
If `Q` has `true` as a value for `sh:qualifiedValueShapesDisjoint` then
the set of sibling shapes for `Q` is defined as the set of all values of the
SPARQL property path `sh:property/sh:qualifiedValueShape` for any shape in `ps`
minus the value of `sh:qualifiedValueShape` of `Q` itself.
The set of sibling shapes is empty otherwise.

Let `$qualifiedValueShape` be a value of `sh:qualifiedValueShape`.
Let `$qualifiedMinCount` be a parameter value for `sh:qualifiedMinCount`.
Let `C` be the number of value nodes `v` where
`v` conforms to `$qualifiedValueShape`
and where `v` does not conform to any of the sibling shapes for the *current* shape,
i.e. the shape that `v` is validated against and which has `$qualifiedValueShape` as its value for `sh:qualifiedValueShape`.
A failure MUST be produced if any of the said conformance checks produces a failure.
Otherwise, there is a validation result if `C` is less than `$qualifiedMinCount`.
The constraint component for `sh:qualifiedMinCount` is `sh:QualifiedMinCountConstraintComponent`.

Let `$qualifiedMaxCount` be a parameter value for `sh:qualifiedMaxCount`.
Let `C` be as defined for `sh:qualifiedMinCount` above.
A failure MUST be produced if any of the said conformance checks produces a failure.
Otherwise, there is a validation result if `C` is greater than `$qualifiedMaxCount`.
The constraint component for `sh:qualifiedMaxCount` is `sh:QualifiedMaxCountConstraintComponent`.

*The remainder of this section is non-normative.*

In the following example shape can be used to specify the condition that the property `ex:parent` has exactly two values,
and at least one of them is female.

**Example: Example of the use of sh:qualifiedValueShape, sh:qualifiedMinCount and sh:qualifiedMaxCount to specify qualified cardinality constraints**

```
ex:QualifiedValueShapeExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:QualifiedValueShapeExampleValidResource ;
    sh:property ex:QualifiedValueShapeExampleShape-parent ;
.
ex:QualifiedValueShapeExampleShape-parent
    a sh:PropertyShape ;
    sh:path ex:parent ;
    sh:minCount 2 ;
    sh:maxCount 2 ;
    sh:qualifiedValueShape [
        sh:path ex:gender ;
        sh:hasValue ex:female ;
    ] ;
    sh:qualifiedMinCount 1 ;
.
							
```

```
ex:QualifiedValueShapeExampleValidResource
    ex:parent ex:John ;
    ex:parent ex:Jane .

ex:John
    ex:gender ex:male .

ex:Jane
    ex:gender ex:female .
							
```

The following example illustrates the use of `sh:qualifiedValueShapesDisjoint`
to express that a hand must have at most 5 values of `ex:digit` (expressed using `sh:maxCount`),
and exactly one of them must be an instance of `ex:Thumb` while exactly 4 of them must be an instance of `ex:Finger`
but thumbs and fingers must be disjoint.
In other words, on a hand, none of the fingers can also be counted as the thumb.

**Example: Example of the use of sh:qualifiedValueShapesDisjoint**

```
ex:HandShape
    a sh:NodeShape ;
    sh:targetClass ex:Hand ;
    sh:property [
        sh:path ex:digit ;
        sh:maxCount 5 ;
	] ;
    sh:property [
        sh:path ex:digit ;
        sh:qualifiedValueShape [ sh:class ex:Thumb ] ;
        sh:qualifiedValueShapesDisjoint true ;
        sh:qualifiedMinCount 1 ;
        sh:qualifiedMaxCount 1 ;
	] ;
	sh:property [
        sh:path ex:digit ;
        sh:qualifiedValueShape [ sh:class ex:Finger ] ;
        sh:qualifiedValueShapesDisjoint true ;
        sh:qualifiedMinCount 4 ;
        sh:qualifiedMaxCount 4 ;
    ] ;
.
							
```

#### 7.8.5 sh:reifierShape, sh:reificationRequired

`sh:reifierShape` can be used to link a property shape with one or more node shapes.
Any reifier must conform to these node shapes.

Constraint Component IRI: `sh:ReifierShapeConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:reifierShape` | The node shape that a reifier for this triple must conform to. The values of `sh:reifierShape` must be well-formed node shapes. If a value for `sh:reifierShape` is given, `sh:path` values are constrained to IRIs. |
| `sh:reificationRequired` | This is an optional parameter of `sh:ReifierShapeConstraintComponent`. If set to `true`, there must be at least one reification value for the focus node/path combination in the data graph. The values of `sh:reificationRequired` in a shape are literals with datatype `xsd:boolean`. |

Let `t` be the triple term (focus node, `$path`, value node).
For each reifier for the triple term `t`, a failure MUST be produced if validating the reifier against the node shape `$reifierShape` with the reifier as focus node produces a failure.
For each reifier `t` that does not conform to `$reifierShape`, there is a validation result with `t` as `sh:value`.

If `$reificationRequired` is set to `true` and there is no reified statement for the triple term `t` in the data graph, there is a validation result with `t` as `sh:value`.

*The remainder of this section is non-normative.*

**Example: Example of sh:reifierShape and sh:reificationRequired**

```
ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:PersonShape-age ;
.
ex:PersonShape-age
    a sh:PropertyShape ;
    sh:path ex:age ;
    sh:datatype xsd:integer ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:reifierShape ex:ProvenanceShape ;
    sh:reificationRequired true ;
.

ex:ProvenanceShape
    a sh:NodeShape ;
    sh:property ex:ProvenanceShape-date ;
    sh:property ex:ProvenanceShape-author ;
.
ex:ProvenanceShape-date
    a sh:PropertyShape ;
    sh:path ex:date ;
    sh:datatype xsd:date ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
.
ex:ProvenanceShape-author
    a sh:PropertyShape ;
    sh:path ex:author ;
    sh:nodeKind sh:IRI ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
.
							
```

In this example the shape `ex:PersonShape` states that all instances of `ex:Person`
must reify its values of `ex:age` with a reifier that conforms to the shape
`ex:ProvenanceShape`, i.e. it needs to specify an `ex:date` and an `ex:author`.

```
ex:Bob
    a ex:Person ; 
    ex:age 23 {|
        ex:date "2019-12-05"^^xsd:date ;
        ex:author ex:Claire
    |}
.
							
```

### 7.9 Other Constraint Components

This section enumerates Core constraint components that do not fit into the other categories.

#### 7.9.1 sh:closed, sh:ignoredProperties

The RDF data model offers a huge amount of flexibility.
Any node can in principle have values for any property.
However, in some cases it makes sense to specify conditions on which properties can be applied to nodes.
The SHACL Core language includes a property called `sh:closed` that can be used to
specify the condition that each value node has values only for those properties that have been explicitly enumerated via the
property shapes specified for the shape via `sh:property`.

Constraint Component IRI: `sh:ClosedConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:closed` | Set to `true` to close the shape. The values of `sh:closed` in a shape are literals with datatype `xsd:boolean` or the IRI `sh:ByTypes`. |
| `sh:ignoredProperties` | Optional SHACL list of properties that are also permitted in addition to those explicitly enumerated via `sh:property`. The values of `sh:ignoredProperties` in a shape must be SHACL lists. Each member of such a list must be a IRI. |

Let `$closed` be a parameter value for `sh:closed`.
Let `$ignoredProperties` be a value for `sh:ignoredProperties`.
  
  
If `$closed` is `true` or `sh:ByTypes` and `P`
is the set of properties defined below,
then there is a validation result for each triple that has a value node as its
subject and a predicate that is not in `P`.
If `$ignoredProperties` has a value then the properties enumerated as members of this SHACL list
are also permitted for the value node.
The validation result MUST have the predicate of the triple as its `sh:resultPath`,
and the object of the triple as its `sh:value`.
  
  
If `$closed` is `true`, then `P` is the set of IRI properties
that can be reached from the current shape via the SPARQL path `sh:property/sh:path`.
  
  
If `$closed` is `sh:ByTypes`, then `P` is the set of IRI properties
that can be reached from the value node via the following algorithm, plus `rdf:type`:

```
function collectProperties(S)
    add all IRI properties that can be reached from S via the SPARQL path
            sh:property/sh:path
    if S is a SHACL instance of rdfs:Class in the shapes graph {
        for each triple in the shapes graph matching (S rdfs:subClassOf ?o)
            collectProperties(?o)
        for each triple in the shapes graph matching (?s sh:targetClass S)
            collectProperties(?s)
    }
    if S is a SHACL instance of sh:NodeShape in the shapes graph
        for each triple in the shapes graph matching (S sh:node ?o)
            collectProperties(?o)

for each rdf:type T of the value node in the data graph
    collectProperties(T)
```

Note that implementations need to avoid infinite loops in the algorithm above by preventing
it from visiting the same `S` twice.

*The remainder of this section is non-normative.*

The following example illustrates the use of `sh:closed` in a shape to specify the condition
that certain focus nodes only have values for `ex:firstName` and `ex:lastName`.
The "ignored" property `rdf:type` would also be allowed.

**Example: Example of the use of sh:closed and sh:ignoredProperties**

```
ex:ClosedShapeExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:Alice, ex:Bob ;
    sh:closed true ;
    sh:ignoredProperties (rdf:type) ;
    sh:property [
        sh:path ex:firstName ;
    ] ;
    sh:property [
        sh:path ex:lastName ;
    ] ;
.
							
```

```
ex:Alice
    ex:firstName "Alice" .

ex:Bob
    ex:firstName "Bob" ;
    ex:middleInitial "J" .
							
```

The use case for `sh:closed sh:ByTypes` includes properties that are declared
in superclasses of the types of the current value node (via `rdfs:subClassOf`),
as well as other shapes that are linked to those types via `sh:targetClass` and
the shapes that can be reached from one node shape to the other via `sh:node`.
Examples for `sh:ByTypes` can be found in the test case library:
[closed-003.ttl](../shacl12-test-suite/tests/core/node/closed-003.ttl),
[closed-004.ttl](../shacl12-test-suite/tests/core/node/closed-004.ttl).

#### 7.9.2 sh:hasValue

`sh:hasValue` specifies the condition that at least one value node is equal to the given RDF term.

Constraint Component IRI: `sh:HasValueConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:hasValue` | A specific required value. |

Let `$hasValue` be a parameter value for `sh:hasValue`.
If the RDF term `$hasValue` is not among the value nodes,
there is a validation result.

*The remainder of this section is non-normative.*

**Example: Example of the use of sh:hasValue**

```
ex:StanfordGraduate
    a sh:NodeShape ;
    sh:targetNode ex:Alice ;
    sh:property ex:StanfordGraduate-alumniOf ;
.
ex:StanfordGraduate-alumniOf
    a sh:PropertyShape ;
    sh:path ex:alumniOf ;
    sh:hasValue ex:Stanford ;
.
							
```

```
ex:Alice
    ex:alumniOf ex:Harvard ;
    ex:alumniOf ex:Stanford .
							
```

#### 7.9.3 sh:in

`sh:in` specifies the condition that each value node is a member of a provided SHACL list.

Constraint Component IRI: `sh:InConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:in` | A SHACL list that has the allowed values as members. Each value of `sh:in` in a shape is a SHACL list. A shape has at most one value for `sh:in`. Each such list *SHOULD* have at least one member. |

Let `$in` be a value of `sh:in`.
For each value node
that is not a member of `$in`,
there is a validation result with the value node as `sh:value`.

*The remainder of this section is non-normative.*

Note that matching of literals needs to be exact, e.g. `"04"^^xsd:byte` does not match `"4"^^xsd:integer`.

**Example: Example of the use of sh:in**

```
ex:InExampleShape
    a sh:NodeShape ;
    sh:targetNode ex:RainbowPony ;
    sh:property ex:InExampleShape-color ;
.
ex:InExampleShape-color
    a sh:PropertyShape ;
    sh:path ex:color ;
    sh:in ( ex:Pink ex:Purple ) ;
.
							
```

```
ex:RainbowPony ex:color ex:Pink .
							
```

#### 7.9.4 sh:rootClass

The condition specified by `sh:rootClass` is that each value node is the given class or a (transitive) subclass of that class.

Constraint Component IRI: `sh:RootClassConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:rootClass` | The root(s) of the class hierarchy that all value nodes must belong to. The values of `sh:rootClass` in a shape are either IRIs or blank nodes that are well-formed SHACL lists where all members are IRIs. |

Let `$rootClass` be a parameter value for `sh:rootClass`.
Let `classes` be a set of IRIs so that
when `$rootClass` is an IRI then the set only consists of exactly that IRI,
and when `$rootClass` is a blank node SHACL list then the set consists of
exactly the members of the list.  
  
For each value node
that is either not an IRI, or an IRI for which there exists no `class` in `classes`
such that the data graph entails
`valueNode rdfs:subClassOf* class`,
there is a validation result with the value node as `sh:value`.

*The remainder of this section is non-normative.*

The `sh:rootClass` constraint is typically used with property shapes
that can have classes as their values (e.g., via `sh:class rdfs:Class`)
to restrict the allowed subclass hierarchy of value nodes.
The given class acts as the upper boundary of the permitted class hierarchy.

**Example: Example of the use of sh:rootClass**

```
ex:RootClassExampleShape
	a sh:NodeShape ;
	sh:targetNode ex:Zoo ;
	sh:property ex:RootClassExampleShape-holds ;
.

ex:RootClassExampleShape-holds
	a sh:PropertyShape ;
	sh:path ex:holds ;
	sh:rootClass ex:Animal ;
.
							
```

```
ex:Animal a rdfs:Class .
ex:Mammal rdfs:subClassOf ex:Animal .
ex:Dog rdfs:subClassOf ex:Mammal .
ex:Plant rdfs:subClassOf ex:Organism .

ex:Zoo
	ex:holds ex:Dog ;
	ex:holds ex:Animal ;
	ex:holds ex:Plant .
							
```

#### 7.9.5 sh:uniqueValuesFor

`sh:uniqueValuesFor` specifies the condition that the values of one or more specified properties of a value node
must be unique within all target nodes of the current shape.

Constraint Component IRI: `sh:UniqueValuesForConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:uniqueValuesFor` | An IRI of a property, or a SHACL list where each member is an IRI of a property. |

Let `$uniqueValuesFor` be a value of `sh:uniqueValuesFor` in shape `S`.
Let `$properties` be the set as follows:
If `$uniqueValuesFor` is an `IRI` then `$properties = { uniqueValuesFor }`.
If `$uniqueValuesFor` is a SHACL list, then `$properties` is the set of the members of that list.
Let `$targetNodes` be the target nodes of `S`.
  
For each value node `V` for which there exists another node in `$targetNodes`
that has exactly the same values for all properties in `$properties` as `V`
there is a validation result.
No result is produced if `V` has no values for any of the properties in `$properties`.

*The remainder of this section is non-normative.*

Note that matching of literals needs to be exact, e.g. `"04"^^xsd:byte` does not match `"4"^^xsd:integer`.
Also note that `sh:uniqueValuesFor` does not prescribe the existence of these values, and is therefore
often combined with a `sh:minCount 1` constraint.

**Example: Example of sh:uniqueValuesFor on a single property**

```
ex:SingleIdExampleShape
    a sh:NodeShape ;
    sh:targetClass ex:Record ;
    sh:property ex:SingleIdExampleShape-id ;
    sh:uniqueValuesFor ex:id ;
.
ex:SingleIdExampleShape-id
    a sh:PropertyShape ;
    sh:path ex:id ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
.
							
```

```
ex:Record1
    a ex:Record ;
    ex:id "One" .

ex:UnrelatedNode
    ex:id "One" .

ex:Record2 
    a ex:Record ;
    ex:id "Two" .

ex:Record3
    a ex:Record ;
    ex:id "Two" .
							
```

In this example, two constraint violations will be reported, for `ex:Record2` and `ex:Record3`
because they have exactly the same values for `ex:id` and are in the target of the same shape.

However, no violation is reported for `ex:id "One"` because `ex:UnrelatedNode` is not an instance
of `ex:Record` and therefore not targeted by `ex:SingleIdExampleShape`.

Note that the computation of the target nodes depends only on the definition of the shape, e.g.
the `sh:targetClass` declaration of the shape that also holds the `sh:uniqueValuesFor` constraint.

**Example: Example of sh:uniqueValuesFor on a pair of two properties**

```
ex:CombinedIdExampleShape
    a sh:NodeShape ;
    sh:targetClass ex:Concept ;
    sh:uniqueValuesFor ( ex:notation ex:inScheme ) ;
.
							
```

```
ex:Concept1
    a ex:Concept ;
    ex:notation "123" ;
    ex:inScheme ex:Scheme1 .

ex:Concept2
    a ex:Concept ;
    ex:notation "123" ;
    ex:inScheme ex:Scheme2 .
							
```

In the example above, no violations are reported because none of the focus nodes of the shape
have the same combination of the two specified properties.

## 8. Non-Validating Shape Characteristics

While the previous sections introduced properties that represent validation conditions,
this section covers properties that are ignored by SHACL processors.
The use of these so-called non-validating properties
is entirely optional and is not subject to formal interpretation contracts.
They may be used for purposes such as form building, code generation or predictable printing of RDF files.

### 8.1 sh:name and sh:description

Property shapes may have one or more values for `sh:name`
to provide human-readable labels for the property in the target where it appears.
If present, tools should prefer such locally specified labels
over globally specified labels at the `rdf:Property` itself.
For example, if a form displays a node that is in the target of a given property shape
with an `sh:name`, then the tool should use the provided name.
The values of `sh:name` must be literals with datatype
`xsd:string`, `rdf:dirLangString`, or `rdf:langString`.

Similarly, property shapes may have values for `sh:description`
to provide descriptions of the property in the given context.
The values of `sh:description` must be literals with datatype
`xsd:string`, `rdf:dirLangString`, `rdf:langString`, or `rdf:HTML`.

Both `sh:name` and `sh:description` may have
multiple values, but should only have one value per language tag.

Note that `sh:name` and `sh:description` should NOT be used for node shapes.
For those, the properties `rdfs:label` and `rdfs:comment` are well-established
and already used for class definitions.

### 8.2 sh:intent

Shapes may have values for `sh:intent` and those values should be literals
with datatype `xsd:string`, `rdf:langString` or `rdf:dirLangString`.

The property `sh:intent` provides a human-readable description of one or more intended
rules, assumptions, or constraints associated with a shape.

Unlike `rdfs:comment`, which may include general documentation or editorial text,
and unlike `sh:description`, which describes the meaning of a property value,
`sh:intent` is specifically intended to capture individual rule-like statements that express
the intended semantics of a shape.

Multiple values of `sh:intent` may be provided to represent distinct intended rules.
Some of these rules may overlap with constraints that are already expressed formally using SHACL constraint components.
When a value of `sh:intent` represents semantics that are also represented formally in the same
shapes graph, the triple of the `sh:intent` statement can be reified with the property value
`sh:formalized true`.
However, the presence or content of `sh:intent` MUST NOT affect SHACL validation or conformance.

**Example: Examples of sh:intent at a node shape about parents**

```
ex:ParentShape
    a sh:NodeShape ;
    sh:targetObjectsOf ex:parent ;
    rdfs:comment "Represents individuals who have one or more (biological) children."@en ;

    sh:intent "A parent must be strictly older than each of their children."@en ;
    sh:intent "If the age of either the parent or child is unknown, the data should be treated as incomplete rather than valid."@en ;
    sh:intent "Age values are compared in years using the same reference date."@en ;
.
						
```

**Example: Examples of sh:intent at a birth date property shape**

```
ex:Person-birthDate
    a sh:PropertyShape ;
    sh:path ex:birthDate ;
    sh:datatype xsd:date ;
    sh:maxCount 1 ;
    sh:description "The date on which the person was born."@en ;

    sh:intent "Each person has at most one birth date."@en {| sh:formalized true |} ;
    sh:intent "The birth date must not be in the future."@en ;
    sh:intent "The birth date should reflect the legal date of birth, not an estimated or approximate value."@en ;
.
						
```

In this example, the first `sh:intent` is already captured using `sh:maxCount`,
in which case the textual description may have been created by a someone with less technical
knowledge, or intentionally left as duplicate for agents that do not understand SHACL.
The second `sh:intent` is difficult to express formally in SHACL
(without, for example, using the SPARQL function `NOW`).
The third `sh:intent` is impossible for a SHACL engine to verify.

### 8.3 sh:agentInstruction

Shapes may have values for `sh:agentInstruction` and those values should be literals
with datatype `xsd:string`, `rdf:langString`, or `rdf:dirLangString`.

This property can be used to represent textual instructions that can be sent to a software agent
that understands natural language.

**Example: Examples of sh:agentInstruction**

```
ex:FootballPlayer
    a sh:ShapeClass ;
    sh:agentInstruction "Don't confuse this with American Football or Rugby — this is about soccer."@en ;
    sh:agentInstruction "When populating instances of this class, look up matching values from Wikidata."@en ;
    sh:agentInstruction "Additional statistics can be found at the World Soccer Database."@en ;
.
						
```

**Note:** This property may be used, together with similar textual descriptions from `rdfs:comment`,
`sh:description`, `rdfs:label`, `sh:name`, `sh:intent`, as well as `sh:message`,
to instruct a software agent about the semantic interpretation of shapes.

### 8.4 sh:codeIdentifier

Shapes may have one value for `sh:codeIdentifier`
to suggest a name that can be used for a representation of the shape in APIs, query languages
and similar programmatic access.
The value of `sh:codeIdentifier` is a literal with datatype `xsd:string`
where the string matches the regular expression `^[a-zA-Z_][a-zA-Z0-9_]*$`.

**Note:** A typical use case would be to generate GraphQL query
schemas from shapes, mapping property shapes to GraphQL fields.
By default such schema generators could use the local name of the
`sh:path`, but it should use the `sh:codeIdentifier` if present.
In the case of complex path expressions an explicit `sh:codeIdentifier` is strongly recommended.
Similar requirements exist for API generators, for example in Java, JavaScript or Python.

### 8.5 sh:unit

Shapes may have values for the property `sh:unit` to indicate a unit of
measure, currency or similar information about the value nodes.
The values of `sh:unit` can be either literals with datatype `xsd:string`
or `rdf:langString` or `rdf:dirLangString`, or IRIs.
SHACL 1.2 does not prescribe specific values for `sh:unit` because, at the time of writing (2026),
there was no official W3C standard to represent them uniformly, and multiple standards exist outside of the W3C.

For SHACL 1.2, the following recommendations are given:

- For units of measure a value of `sh:unit` may be an `xsd:string`
  literal that exactly matches a code defined in [UCUM](http://ucum.org);
  for example, `sh:unit "cm"`.
- For currencies, a value of `sh:unit` may be an `xsd:string` literal
  that exactly matches a code defined in [ISO 4217](https://www.iso.org/iso-4217-currency-codes.html);
  for example, `sh:unit "AUD"`.
- A value of `sh:unit` may be an IRI defined by the
  [QUDT](https://qudt.org/) or a similar units vocabulary;
  for example `sh:unit qudt:CentiM`.
- In addition to these canonical values, there may be additional language-tagged literals
  with abbreviations or display names that are commonly used in the selected language(s);
  for example, `"Zoll"@de` in addition to `"in"` for inches.

While these syntax rules are intentionally left flexible, specific applications may enforce more specific rules;
for example, by declaring a `sh:class qudt:Unit` constraint on the `sh:unit` property.

User interface tools based on SHACL can use the values of `sh:unit` to render values.
Depending on a user's locale such tools may even automatically convert between units,
or even allow data entry in units different than those that the actual values will be stored as.

**Example: Example unit declarations in property shapes**

```
ex:Fridge
    a sh:ShapeClass ;
    sh:property ex:Fridge-height ;
    sh:property ex:Fridge-price ;
.
ex:Fridge-height
    a sh:PropertyShape ;
    sh:path ex:height ;
    sh:datatype xsd:decimal ;
    sh:unit "cm"@en ;
.
ex:Fridge-price
    a sh:PropertyShape ;
    sh:path ex:price ;
    sh:datatype xsd:decimal ;
    sh:unit "EUR"@en ;
.
						
```

```
ex:SomeFridge
    a ex:Fridge ;
    ex:height 180.5 ;
    ex:price 999.95 ;
.
						
```

For this example, a user interface may render the height as

`180.5 cm (71 in)`

or, for US-based visitors, as

`71 in (180.5 cm)`

**Note:** While SHACL Core does not specify specific semantics for `sh:unit`, some
SHACL-based extensions may use units for other purposes, including validation.
For example, a shape could be defined that enforces a `sh:minInclusive 0`
constraint on any literal for which the property declares `sh:unit "K"`.

The following variation of the example above uses a node shape to encapsulate
a reusable definition of "price in Euros" that includes the unit but also constraints
such as the minimum value.

**Example: A node shape with a unit declaration**

```
ex:PriceEUR
    a sh:NodeShape ;
    sh:datatype xsd:decimal ;
    sh:minInclusive "0"^^xsd:decimal ;
    sh:unit "EUR"@en ;
.
ex:Fridge-price
    a sh:PropertyShape ;
    sh:path ex:price ;
    sh:node ex:PriceEUR ;
.
						
```

### 8.6 sh:order

Property shapes may have one value for the property `sh:order`
to indicate the relative order of the property shape for purposes such as form building.
The values of `sh:order` are literals with datatype `xsd:decimal` or `xsd:integer`.
`sh:order` is not used for validation purposes.
If present at property shapes, the recommended use of `sh:order` is to sort the
property shapes in an ascending order in user interfaces, for example so that properties with smaller order are
placed above or to the start (left in left-to-right languages) of properties with larger order.

**Note:** `sh:order` provides a general mechanism to specify the relative order of elements in a list.
Although `sh:order` does not impact SHACL validation, it may be used with any type of
subjects and carry stronger semantics in other specifications.

### 8.7 sh:group

Property shapes may link to a SHACL instance of the class `sh:PropertyGroup`
using the property `sh:group` to indicate that
the shape belongs to a group of related property shapes.
Each group may have additional triples that serve application purposes,
such as an `rdfs:label` for form building.
Groups may also have an `sh:order` property to indicate
the relative ordering of groups within the same form.

The following example illustrates the use of these various features together.

**Example: Example of sh:order and sh:group for form building**

```
ex:PersonFormShape
    a sh:NodeShape ;
    sh:property ex:PersonFormShape-firstName ;
    sh:property ex:PersonFormShape-lastName ;
    sh:property ex:PersonFormShape-streetAddress ;
    sh:property ex:PersonFormShape-locality ;
    sh:property ex:PersonFormShape-postalCode ;
.
ex:PersonFormShape-firstName
    a sh:PropertyShape ;
    sh:path ex:firstName ;
    sh:name "first name"@en ;
    sh:description "The person's given name(s)"@en ;
    sh:order 0 ;
    sh:group ex:NameGroup ;
.
ex:PersonFormShape-lastName
    a sh:PropertyShape ;
    sh:path ex:lastName ;
    sh:name "last name"@en ;
    sh:description "The person's last name"@en ;
    sh:order 1 ;
    sh:group ex:NameGroup ;
.
ex:PersonFormShape-streetAddress
    a sh:PropertyShape ;
    sh:path ex:streetAddress ;
    sh:name "street address"@en ;
    sh:description "The street address including number"@en ;
    sh:order 11 ;
    sh:group ex:AddressGroup ;
.
ex:PersonFormShape-locality
    a sh:PropertyShape ;
    sh:path ex:locality ;
    sh:name "locality"@en ;
    sh:description "The city or town of the address"@en ;
    sh:order 12 ;
    sh:group ex:AddressGroup ;
.
ex:PersonFormShape-postalCode
    a sh:PropertyShape ;
    sh:path ex:postalCode ;
    sh:name "postal code"@en ;
    sh:name "zip code"@en-us ;
    sh:description "The postal code of the locality"@en ;
    sh:order 13 ;
    sh:group ex:AddressGroup ;
.

ex:NameGroup
    a sh:PropertyGroup ;
    sh:order 0 ;
    rdfs:label "Name"@en ;
.

ex:AddressGroup
    a sh:PropertyGroup ;
    sh:order 1 ;
    rdfs:label "Address"@en ;
.
						
```

A form building application may use the information above to display information as follows:

Name

|  |  |
| --- | --- |
| **first name:** | John |
| **last name:** | Doe |

Address

|  |  |
| --- | --- |
| **street address:** | 123 Silverado Ave |
| **locality:** | Cupertino |
| **zip code:** | 54321 |

Note that the same information would be generated by the following example,
which changes the order of the triples but not the `sh:order` values:

**Example: Example of the use of sh:order and sh:group for form building**

```
ex:PersonFormShape
    a sh:NodeShape ;
    sh:property [
        sh:path ex:lastName ;
        sh:name "last name"@en ;
        sh:description "The person's last name"@en ;
        sh:order 1 ;
        sh:group ex:NameGroup ;
    ] ;
    sh:property [
        sh:path ex:firstName ;
        sh:name "first name"@en ;
        sh:description "The person's given name(s)"@en ;
        sh:order 0 ;
        sh:group ex:NameGroup ;
    ] ;
    sh:property [
        sh:path ex:postalCode ;
        sh:name "postal code"@en ;
        sh:name "zip code"@en-us ;
        sh:description "The postal code of the locality"@en ;
        sh:order 13 ;
        sh:group ex:AddressGroup ;
    ] ;
    sh:property [
        sh:path ex:streetAddress ;
        sh:name "street address"@en ;
        sh:description "The street address including number"@en ;
        sh:order 11 ;
        sh:group ex:AddressGroup ;
    ] ;
    sh:property [
        sh:path ex:locality ;
        sh:name "locality"@en ;
        sh:description "The city or town of the address"@en ;
        sh:order 12 ;
        sh:group ex:AddressGroup ;
    ] ;
.

ex:AddressGroup
    a sh:PropertyGroup ;
    sh:order 1 ;
    rdfs:label "Address"@en ;
.

ex:NameGroup
    a sh:PropertyGroup ;
    sh:order 0 ;
    rdfs:label "Name"@en ;
.
						
```

**Note:** For predicates that accept literals of type `xsd:string`, `rdf:langString`, `rdf:dirLangString`, or `rdf:HTML`, users should avoid `xsd:string` in favor of `rdf:langString` or `rdf:dirLangString`. Using language tags and, where appropriate, directionality markers is recommended to support internationalization and correctly handle bidirectional text.

## A. Summary of SHACL Syntax Rules

This section enumerates all normative syntax rules of SHACL.
This section is automatically generated from other parts of this spec and hyperlinks are provided back
into the prose if the context of the rule in unclear.
Nodes that violate these rules in a shapes graph are ill-formed.

| Syntax Rule Id | Syntax Rule Text |
| --- | --- |

## B. SHACL Shapes to Validate Shapes Graphs

The SHACL 1.2 Overview's [SHACL-SHACL Appendix](../shacl12-overview/#shacl-shacl)
describes SHACL graphs that can be used to validate other SHACL Shapes graphs and thus may enforce many of the syntactic
constraints related to RDF data aiming to conform to the various SHACL specifications.

The SHACL-SHACL shapes graphs are available per specification and also as a bundled 'union' at
<http://www.w3.org/ns/shacl-shacl>, as indicated in
the Overview's appendix.

## C. Summary of SHACL Core Validators

This section enumerates all normative validators of SHACL Core.
This section is automatically generated from other parts of this spec and hyperlinks are provided back
into the prose if the context of the validator in unclear.

| Validators by Constraint Component |
| --- |

## D. Security and Privacy Considerations

Like most RDF-based technologies, SHACL processors may operate on graphs that are combined
from various sources. Some applications may have an open "linked data" architecture and dynamically
assemble RDF triples from sources that are outside of an organization's network of trust.
Since RDF allows anyone to add statements about any resource, triples may modify the originally
intended semantics of shape definitions or nodes in a data graph and thus lead to misleading results.
Protection against this (and the following) scenario can be achieved by only using trusted
and verified RDF sources and eliminating the possibility that graphs are dynamically added via
`owl:imports` and `sh:shapesGraph`.

## E. Acknowledgements

The original SHACL core specification was produced by the RDF Data Shapes Working Group.
See its [Acknowledgements section](https://www.w3.org/TR/2017/REC-shacl-20170720/#ack).

## F. Changes between the original SHACL Core and SHACL 1.2 Core

- Introduced node expressions as an extension point to dynamically compute lists of nodes. Generalized `sh:targetNode`, `sh:deactivated` and `sh:defaultValue`, and introduced `sh:values` to support node expressions.
- Added the new constraint component [`sh:singleLine`](#SingleLineConstraintComponent), see [Issue 177](https://github.com/w3c/data-shapes/issues/177)
- Added the new constraint component [`sh:someValue`](#SomeValueConstraintComponent), see [Issue 178](https://github.com/w3c/data-shapes/issues/178)
- Added the new class [`sh:ShapeClass`](#ShapeClass) for implicit class targets; see [Issue 212](https://github.com/w3c/data-shapes/issues/212)
- Moved SPARQL-based validators from Core to an Appendix of SHACL-SPARQL; see [Issue 271](https://github.com/w3c/data-shapes/issues/271)
- The 4 [property pair constraint components](#core-components-property-pairs) now also support property paths as parameters; see [Issue 281](https://github.com/w3c/data-shapes/issues/281)
- Added new [List constraint components](#core-components-list), see [Issue 391](https://github.com/w3c/data-shapes/issues/391) and [Issue 414](https://github.com/w3c/data-shapes/issues/414)
- Added the new value `sh:ByTypes` for [`sh:closed`](#ClosedConstraintComponent); see [Issue 172](https://github.com/w3c/data-shapes/issues/172)
- The values of [`sh:class`](#ClassConstraintComponent) and [`sh:datatype`](#DatatypeConstraintComponent) can now also be lists, indicating a union of choices; see [Issue 160](https://github.com/w3c/data-shapes/issues/160)
- The values of [`sh:nodeKind`](#NodeKindConstraintComponent) can now also be lists, indicating a union of choices; see [Issue 407](https://github.com/w3c/data-shapes/issues/407)
- Added the new constraint component [`sh:ReifierShape`](#ReifierShapeConstraintComponent); see [Issue 300](https://github.com/w3c/data-shapes/issues/300)
- Added parameter [6.3 Graph for rdfs:subClassOf Triples](#subClassOfInShapesGraph) to look up rdfs:subClassOf triples in the union of the shapes graph and the data graph; see [Issue 185](https://github.com/w3c/data-shapes/issues/185)
- Generalized [8.6 sh:order](#order) to also allow xsd:integers; see [Issue 479](https://github.com/w3c/data-shapes/issues/479)
- Added new [`sh:conformanceDisallows` property](#conformanceDisallows) to the validation report; see [Issue 453](https://github.com/w3c/data-shapes/issues/453)
- Added annotation property [8.4 sh:codeIdentifier](#codeIdentifier); see [Issue 559](https://github.com/w3c/data-shapes/issues/559)
- Added the target types [3.1.3.6 Where Targets (sh:targetWhere)](#targetWhere) and [3.1.3.7 Explicit shape targets (sh:shape)](#explicit-shape-target); see [Issue 517](https://github.com/w3c/data-shapes/issues/517)
- Added support for units and currencies [8.5 sh:unit](#unit); see [Issue 709](https://github.com/w3c/data-shapes/issues/709)
- Added support for [8.3 sh:agentInstruction](#agentInstruction) and [8.2 sh:intent](#intent), see [Issue 725](https://github.com/w3c/data-shapes/issues/725)
- Added support for `rdf:dirLangString` to [7.4.6 sh:uniqueLang](#UniqueLangConstraintComponent), see [Issue 737](https://github.com/w3c/data-shapes/issues/737)
- Added the new constraint component [`sh:rootClass`](#RootClassConstraintComponent), see [Issue 792](https://github.com/w3c/data-shapes/issues/792)
- Added the new constraint component [`sh:subsetOf`](#SubsetOfConstraintComponent), see [Issue 786](https://github.com/w3c/data-shapes/issues/786)
- Added the graph types `sh:DataGraph` and `sh:ShapesGraph`; see [Issue 169](https://github.com/w3c/data-shapes/issues/169)
- Added the new constraint component [`sh:uniqueValuesFor`](#UniqueValuesForConstraintComponent), see [Issue 661](https://github.com/w3c/data-shapes/issues/661)
- Added support for `owl:versionIRI` in [shapes graph](#shapes-graph) imports, and expanded the definition of well-formed shapes graphs to include import closure constraints from owl2-syntax; see [Issue 830](https://github.com/w3c/data-shapes/issues/830)
