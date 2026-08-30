<!-- https://w3c.github.io/data-shapes/shacl12-rules/ — W3C editors' draft, fetched 2026-08-17 -->

This document defines *SHACL Rules*.

SHACL, the Shapes Constraint Language, is a language for describing the structure
of RDF graphs.
SHACL may be used for a variety of purposes such as validating, inferencing,
modeling domains, generating ontologies to inform other agents, building user
interfaces, generating code, and integrating data.

SHACL Rules provides inferencing with the generation of new RDF data from a
combination of a set of rules and a base data graph. Rules can be expressed as RDF
or in the Shape Rules Language (SRL).

This specification is published by the
[Data Shapes Working Group](https://www.w3.org/groups/wg/data-shapes/).

## SHACL Specifications

This specification is part of the SHACL 1.2 family of specifications. See the [SHACL 1.2 Overview](https://w3c.github.io/data-shapes/shacl12-overview/) for a more detailed introduction to them.

The specifications are as follows:

**Working Drafts:**

[SHACL 1.2 Core](https://www.w3.org/TR/shacl12-core/)
:   defines the Core of SHACL

[SHACL 1.2 SPARQL Extensions](https://www.w3.org/TR/shacl12-sparql/)
:   defines SPARQL-related extensions of SHACL

[SHACL 1.2 Node Expressions](https://www.w3.org/TR/shacl12-node-expr/)
:   defines expressions used to derive focus nodes and value nodes in SHACL

[SHACL 1.2 Rules](https://www.w3.org/TR/shacl12-rules/)
:   defines SHACL's methods of rule-based inference

[SHACL 1.2 UI](https://w3c.github.io/data-shapes/shacl12-ui/)
:   defines SHACL's use for User Interface generation

[SHACL 1.2 Profiling](https://w3c.github.io/data-shapes/shacl12-profiling/)
:   defines the use of SHACL for profiling data, including SHACL data

**Working Group Note Drafts:**

[SHACL 1.2 Overview](https://w3c.github.io/data-shapes/shacl12-overview/)
:   overviews the set of SHACL specifications

[SHACL 1.2 Compact Syntax](https://w3c.github.io/data-shapes/shacl12-cs/)
:   defines an RDF syntax for expressing SHACL concepts

**Note:** Implementers can partially check their level of conformance with the above specifications by successfully passing
the test cases of the [SHACL 1.2 test suite](https://github.com/w3c/data-shapes/tree/gh-pages/shacl12-test-suite).
Note, however, that passing all the tests in the test suite does not imply complete conformance to the specifications.
It only implies that the implementation conforms to the aspects tested by the test suite.

## 1. Introduction

This document introduces inference rules for SHACL 1.2, a mechanism for
deriving new RDF triples from existing RDF data through declarative rules.
The document defines the syntax and semantics of rule-based inference.

Implementations of SHACL Rules provide two operations.
The *infer* operation that applies the rules to a given
*base graph* and produces an *inference graph* containing the
RDF triples derived by rule execution.
Combining the inference graph with the base graph is optional and
left to users. The *query* operation determines whether a
given goal pattern can be derived from the base graph using the rules.

SHACL Rules allow the use of new RDF terms, including blank nodes,
that can be used in triple templates in the head of rules.

SHACL Rules also support constructs, such as negation as failure,
that could lead to different inferred graphs depending on the order in which
rules are executed. To avoid this, rules are evaluated using the technique
of *stratification*, which establishes a single, implicit ordering
among rules, ensuring that the same inference graph is always produced.

### 1.1 Terminology

The following other specifications provide fundamental terminology
that is used in this document:

- RDF12-CONCEPTS
- SPARQL12-QUERY

### 1.2 Document Conventions

Some examples in this document use RDF12-Turtle.

Within this document, the following namespace prefix bindings are used:

| Prefix | Namespace |
| --- | --- |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` |
| `srl:` | `http://www.w3.org/ns/shacl-rules#` |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` |
| `sparql:` | `http://www.w3.org/ns/sparql#` |
| `ex:` | `http://example/` |

Throughout the document, color-coded boxes containing RDF graphs in
Turtle will appear. These fragments of Turtle documents use the prefix
bindings given above.

```
        # This box represents rules
```

```
       # This box represents input data
```

```
        # This box represents inferred data
```

## 2. Conformance

This specification defines conformance criteria for:

- [SRL Rule Set evaluation](#rule-set-evaluation)
- [Shape Rules language syntax](#shape-rules-syntax)

A conforming SRL document is an
RDF string that
conforms to the [grammar](#grammar) starting with the
[`RuleSet`](#rRuleSet)
production as defined in
[7. Shape Rules Language Grammar](#shapes-rules-grammar).

**Note:** This specification does not define how SPARQL-RL
processors handle non-conforming rule sets.

## 3. SHACL Rules

SHACL rules infer new triples given a base graph and a rule set.
The output of evaluation is an inference graph containing the derived
triples that do not appear in the base graph.

Each rule has a pattern, called the body, and a result
template, called the head.
A rule is executed by finding the values for variables in the body
so that the body matches the combined base graph and
any inferred triples from the execution up to this point.
These values are then used to instantiate the triple templates
in the rule head to produce new inferred triples.

The rules are executed until no more triples are inferred,
and rules may be executed more than once as new inferred triples
become available.

SHACL Rules execution is defined so that the order of rule execution
does not lead to different outcomes when creating new RDF terms,
including new blank nodes, nor when testing for the absence of a
pattern. In other words, the same inference graph is produced
regardless of the order of rule execution.

SHACL Rules has both a RDF syntax, as well as a human-friendly syntax,
inspired by SPARQL12-QUERY.
Rule set evaluation contains elements similar to SPARQL, with differences
in the details to ensure that the same inference graph is produced
regardless of the order of rule execution.

### 3.1 Basic Patterns

The examples in this section describe software components and
their dependencies: a frontend calls an application server, and
the application server queries a database that has a known
vulnerability.

In this first example, we have the following data graph and rule set:

**Example: Basic Example**

```
            :frontend :callsService :app .
            :app      :queriesDatabase :db .
            :db       :hasVulnerability :vuln1 .
```

```
            RULE { ?x :dependsOn ?y } WHERE { ?x :callsService ?y }
            RULE { ?x :dependsOn ?y } WHERE { ?x :queriesDatabase ?y }
```

```
            :frontend :dependsOn :app .
            :app      :dependsOn :db .
```

The above rules, applied to the data, will conclude that
`:frontend` depends on `:app`, and that `:app` depends on
`:db`, whatever the kind of dependency.

We can then derive `:exposedTo` relationships by adding a rule that depends
on `:dependsOn` triples produced by the other rules (see also [4.3 Rule Dependency](#rule-dependency)) below:

**Example: Depending on inferred triples**

```
            :frontend :callsService :app .
            :app      :queriesDatabase :db .
            :db       :hasVulnerability :vuln1 .
```

```
            RULE { ?x :dependsOn ?y } WHERE { ?x :callsService ?y }
            RULE { ?x :dependsOn ?y } WHERE { ?x :queriesDatabase ?y }
            RULE { ?x :exposedTo ?v } WHERE { ?x :dependsOn ?y . ?y :hasVulnerability ?v }
```

```
            :app      :exposedTo :vuln1 .
            :frontend :dependsOn :app .
            :app      :dependsOn :db .
```

### 3.2 Recursion

The `:exposedTo` rule of the previous section only reaches direct
dependencies: `:frontend` does not depend directly on `:db`, so
no `:exposedTo` triple is inferred for `:frontend`.
To propagate exposure along dependency chains of any length, we
replace that rule with two rules: a component is exposed to a
vulnerability it has, and a component is exposed to any
vulnerability that its direct dependencies are exposed to:

**Example: Rule Recursion**

```
            :frontend :callsService :app .
            :app      :queriesDatabase :db .
            :db       :hasVulnerability :vuln1 .
```

```
            RULE { ?x :dependsOn ?y } WHERE { ?x :callsService ?y }
            RULE { ?x :dependsOn ?y } WHERE { ?x :queriesDatabase ?y }
            RULE { ?x :exposedTo ?v } WHERE { ?x :hasVulnerability ?v }
            RULE { ?x :exposedTo ?v } WHERE { ?x :dependsOn ?y . ?y :exposedTo ?v }
```

```
            :db       :exposedTo :vuln1 .
            :app      :exposedTo :vuln1 .
            :frontend :exposedTo :vuln1 .
            :frontend :dependsOn :app .
            :app      :dependsOn :db .
```

Compared with the previous example, this adds
`:db :exposedTo :vuln1` — the database is exposed to its
own vulnerability — and `:frontend :exposedTo :vuln1`:
the exposure reaches `:frontend` through the chain of
dependencies, however long the chain.

This last rule is a *recursive* rule: the body of the rule
depends on the head of the rule.

### 3.3 Filtering

We can use expressions in the body of rules to restrict the values of variables
in the matching of the body.
For example, given the severity of each vulnerability,
we can give a status to components that are exposed to a severe
vulnerability:

**Example: Filtering**

```
            :app1 :exposedTo :vuln1 .
            :app2 :exposedTo :vuln2 .
            :vuln1 :severity 9.1 .
            :vuln2 :severity 4.3 .
```

```
            RULE { ?x :status :criticallyExposed }
            WHERE {
                ?x :exposedTo ?v .
                ?v :severity ?s .
                FILTER(?s >= 9.0)
            }
```

```
            :app1 :status :criticallyExposed .
```

`FILTER` evaluates an expression and keeps the current
set of variable bindings if the expression evaluates to true, and it discards the
current set of variable bindings if the expression evaluates to false.
This is the same as the
`FILTER` operation of SPARQL
and SHACL Rules provides many of the same functions and operators as SPARQL.

### 3.4 Negation

Negation allows you to specify a pattern that must not match.
This is called "negation as failure".

In order to evaluate a negation element, the rules evaluation algorithm
ensures that all the rules that could produce triples matching the pattern
in the negation element have been completed. This is called
*stratification* and ensures that the negation is based
on all the relevant possible triples, whether from the data or
in the negation element have been completed. The rule containing the negation is said to \_depend\_ on the rules generating these triples (see [4.3 Rule Dependency](#rule-dependency) below).

**Example: Negation as failure**

```
            :app rdf:type :Component ;
            :status :criticallyExposed .

            :logger rdf:type :Component .
```

```
            RULE { ?x :status :safeToDeploy }
            WHERE {
                ?x rdf:type :Component .
                NOT { ?x :status :criticallyExposed }
            }
```

```
            :logger :status :safeToDeploy .
```

### 3.5 Assignment and Creating RDF Terms

Assignment allows you to assign the result of an expression to a variable
in the body of a rule. This can be used to create new RDF terms based
on the data.

**Example: Assignment**

```
            RULE { ?v :riskScore ?r }
            WHERE {
                ?v :severity ?s .
                ?v :exploitLikelihood ?p .
                SET ( ?r := ?s * ?p )
            }
```

Blank nodes can be used in the rule head, and each generates a fresh blank node
each time rule evaluation generates triples.

**Example: Blank node in the rule head**

```
            RULE { [] rdf:type :Notification ; :concerns ?x }
            WHERE { ?x :status :criticallyExposed }
```

Rules involving assignments and rules that create blank nodes in
their rule head are run-once rules.
Such rules are run after all the rules that could produce data that they depend on,
and before any rules that depend on the data they produce.
Rules that involve blank nodes in the rule head also create new
RDF terms and are run-once rules.

This condition ensures that such rules do not loop back to themselves and cause an unbounded number of RDF terms.

If evaluating the expression in an assignment causes an error,
then the current solution mapping is rejected by the assignment.

### 3.6 Importing Rule Sets

A SHACL rule set can incorporate other rule sets by
including their URLs in the rule set imports of the rule set.
This allows rules to be structured into libraries shared between rule sets.

The `IMPORTS` statements of a rule set are processed before any of the rules
in the rule set are evaluated. During the importing step, if an imported rule set
has its own imports, those are also processed recursively.
Traversing `IMPORTS` statements during the processing of rule sets may lead to
cyclic imports. A rule set is imported only once;
cycles in the import statements graph do not lead to infinite loops.

Support for importing rule sets is optional for SRL processors.
See [4.5 Processing Imports](#process-imports) for further details.

### 3.7 Data Blocks

Data blocks allow concisely providing RDF triples directly to the rule set evaluation.
Triples in datablocks are added to the inference graph and are available for
matching in the body of rules.

For example, a rule set can ship with known facts asserted
directly, rather than derived from data:

**Example: Include data in a rule set**

```
            DATA {
                # Versions 2.0.0 and earlier suffer a known vulnerability
                # and are assumed critically exposed.
                :appV2 rdf:type :Component ;
                       :version "2.0.0" ;
                       :status :criticallyExposed .
            }
```

**Note:** A data block is equivalent to a rule with an empty body:
its triples are part of the inference graph without any rule
being evaluated.

### 3.8 Evaluation of a Rule Set

Rules are organized into rule sets.
A rule set and a data graph (the base graph) are inputs to evaluation.
The output is a graph, called the inference graph,
which is the set of triples that do not appear in the data graph.

During evaluation, triples inferred based on one rule are
available for matching in other rules.
Rule set evaluation proceeds until the inference graph
contains all the possible triples from the inputs of
rule set and data graph.

Evaluation starts with two steps to
[prepare a rule set](#evaluation-preparation)
before the rules themselves are evaluated:

1. Where supported, the imports of the input rule set are resolved to form a
   rule set that includes all the rules of all
   imported rule sets.
   A processor MUST signal an error if any import is not acceptable
   to the processor ([4.5 Processing Imports](#process-imports)).
2. A stratification is calculated ([4.4.2 Stratification Algorithm](#stratification-algorithm)
   so that negation elements and assignment elements produce consistent,
   predictable outcomes. Stratification involves inspecting the dependencies
   between rules
   ([4.3.1 Dependency Graph](#dependency-graph)).

Once a rule set has been prepared, evaluation proceeds
by taking each layer from the stratification, in order,
evaluating the rules in that layer to completion,
and then moving on to the next layer.

### 3.9 Matching Ground Data

Ground data is the triples in the base graph.
During [rule set evaluation](#rule-set-evaluation) it may be
necessary to pattern match only on the original, not on any inferred
triples.

An example of this is setting a default value.
The rule must test whether the base graph already contains a value and, if not,
the rule can then calculate a default value.

**Example: Ground Data with NOT**

```
            :A :distanceMiles 5 .
            :A :distanceKilometers 8 .
            :B :distanceMiles 10 .
```

```
            RULE  { ?x :distanceKilometers ?kilometers }
            WHERE {
                ?x :distanceMiles ?miles . 
                NOT DATA { ?x :distanceKilometers ?km }
                SET ( ?kilometers := xsd:integer(?miles *  1.60934))
            }
```

```
            :B :distanceKilometers 16 .
```

Using `NOT DATA` allows other parts of the rule body to match inferred triples.
It is also possible to perform all rule body matching against the base graph by
using `WHERE DATA`.
Such rules then only rely on matching from the base graph.

**Example: Ground Data with WHERE**

```
            RULE  { ?x :distanceKilometers ?kilometers }
            WHERE DATA {
                ?x :distanceMiles ?originalMiles .
                NOT { ?x :distanceKilometers ?km } 
                SET ( ?kilometers := xsd:integer(?originalMiles *  1.60934))
            }
```

### 3.10 SHACL Integration

The `FOR ?v IN <shape>` re-introduces targeting on top of
that model. It ties a single rule to a SHACL shape so the rule
fires only for the shape's target focus nodes that conform to
the shape, with a user-named "focus variable" pre-bound to each
such node.

[Full proposal](https://github.com/w3c/data-shapes/issues/1074)

### 3.11 Relationship between SRL and SPARQL

SRL and SPARQL have a close relationship. SRL is designed to be compatible
with SPARQL, and many of the constructs in SRL are taken from or inspired by SPARQL.
However, there are some differences:

- Rules have additional well-formedness conditions that ensure
  variables are always bound before use.
- The syntax of a rule body is similar to a SPARQL `CONSTRUCT` query, but has
  restrictions such as not having `UNION` or `OPTIONAL` syntax.
  The effect of these can be achieved using well-formed rules
  so that the rule set can be analysed.
  These restrictions ensure that variables are always bound, whereas in a SPARQL
  `CONSTRUCT` query template, triples involving an unbound variable
  are omitted from results yet triples in the same template, with all
  variables bound, still generate output.
- The rule `SET` form and SPARQL `BIND` form have different error
  handling behavior. An error encountered in `SET` causes the
  current solution to be filtered out, whereas `BIND` does not
  set the variable in the current solution.
  `SET(?var := expr)` would be the same as
  SPARQL with
  `BIND(expr AS ?var)` followed by
  `FILTER(BOUND(?var))`.
- The syntax of `NOT` limits the inner body to triple
  patterns and filters, and does not allow nested patterns,
  unlike SPARQL `NOT EXISTS`.
- Some functions are not included in the SRL syntax. There is no
  `COALESCE`, nor `BOUND`. There are no hash functions. There
  is no `RAND`, which has different results each time it is
  called.

  **Note:** `NOW()` is permitted and is defined to return the same
  point in time throughout a rule set evaluation. This is the
  same as `NOW()` in SPARQL.
- Property path syntax only covers paths that can be expanded into triple patterns.
  It does not allow arbitrary length operators `\*` and `+`.
  Arbitrary length paths can be expressed in SHACL Rules
  with recursion as a more general approach.

## 4. Shape Rules Abstract Syntax

The Shape Rules Abstract Syntax is the logical structure of SHACL Rules.
It is used to define the execution algorithm of SHACL Rules.
Each of the two concrete syntax forms of SHACL Rules, the Shape Rules Language (SRL)
and the RDF syntax (SRL/RDF), provides a way to express the abstract syntax.

### 4.1 Elements of the Abstract Syntax

Variable
:   A variable represents a possible RDF term in a triple pattern.
    Variables are also used in expressions.

Expression
:   An expression is a function or a functional form;
    the arguments are RDF terms.
    An expression is evaluated with respect to a solution mapping, giving
    an RDF term as the result.
    Expressions are compatible with
    SHACL list parameter functions
    and with SPARQL expressions.

Data block
:   A data block is a set of triples.
    These triples are added to the inference graph as additional facts and are
    included in the inference process.

Triple template
:   A triple template is 3-tuple where each element is either
    a variable or an RDF term (which might be a triple term).
    The second element of the tuple must be an IRI or a variable.
    Triple templates appear in the head of a rule.

Triple pattern
:   A triple pattern is 3-tuple where each element is either a
    variable or an RDF term (which might be a triple term).
    The second element of the tuple must be an IRI or a variable.

Filter element
:   A filter element is an expression
    that appears as a rule element
    It is used to restrict the values of variables
    in pattern matching.

Triple pattern element
:   A triple pattern element is a triple pattern
    that appears as a rule element.

Negation element
:   A negation element is a rule element.
    It has a negation element body
    comprised of a sequence of triple pattern elements and
    filter elements.

Assignment element
:   An assignment element is a rule element that is
    a pair consisting
    of a variable, called the assignment variable,
    and an expression, called the assignment expression.

Rule element
:   A rule element is any one of
    triple pattern element,
    filter element,
    negation element, or
    assignment element.

Rule head
:   A rule head is a sequence of triple templates.

Rule body
:   A rule body is a sequence of rule elements;
    that is, each sequence element is one of
    a triple pattern element,
    a filter element,
    a negation element,
    or an assignment element.

Rule set imports
:   Rule set imports (often just "imports") are a collection of URLs
    for other rule sets that will be included during evaluation.

Rule
:   A rule is a pair of a rule head (often just "head") and
    a rule body (often just "body").
    A rule can be given a URI to help identify it.

Run-once rule
:   A run-once rule is a rule that is run exactly once at a
    particular point in the evaluation of a rule set.

General rule
:   A general rule is a rule that is not a run-once rule.
    General rules may run more than once during rule set evaluation.

Rule set
:   A rule set is a collection of zero or more rules,
    a collection of zero or more data blocks,
    and a collection of zero or more rule set imports.
    A resolved rule set is a rule set
    which has no imports.
    A resolved rule set is created from another rule set
    by applying the [imports process](#process-imports).

Base graph
:   A base graph is the RDF Graph given as input to the
    evaluation process.

Inference graph
:   An inference graph is an RDF Graph produced by
    a rule set evaluation.
    It contains all inferred triples not present in the base
    graph that are inferred by applying the rule set to the
    base graph.

Rule set evaluation
:   A rule set evaluation is the process of applying a rule set
    to a base graph to produce an inference graph.
    A rule evaluation is the process of evaluating a rule once.
    Evaluating a rule produces all the triples given by the rule head
    given the evaluation of the rule body, regardless of whether a
    triple is in the base graph, already inferred during rule set evaluation,
    or is a new inferred triple.
    During rule set evaluation, a rule may be evaluated more than once.

The Shape Rules Language provides two operations, infer and query.

Infer
:   Infer is the operation that applies a rule set to a given
    base graph and produces an inference graph containing inferred
    triples. It is applies the full rule set evaluation.

Query
:   Query is the operation that determines whether a given goal
    pattern can be derived from a base graph using the rule
    set.
    It may not evaluate all rules; instead, it may only evaluate
    rules that are necessary to answer the query goal.

    Query is equivalent to performing an infer operation
    followed by matching the goal pattern to the combined base
    graph and inference graph.

In a triple pattern or a triple template,
position 1 of the tuple is informally called the *subject*,
position 2 is informally called the *predicate*, and
position 3 is informally called the *object*.

**Note:** The elements of a sequence of rule elements are labelled starting at 1.

The following notation is used for the various components of rule sets and rules.

Component Notation

| Component | Usage |
| --- | --- |
| `ruleset.rules` | The rules of a rule set. |
| `ruleset.data` | The RDF graph formed by union of the data blocks in the rule set. |
| `ruleset.imports` | The set of imports of a rule set. |
| `rule.head` | The triple templates of the rule head. |
| `rule.body` | The rule elements of the rule. |
| `rule.data` | A boolean flag; if false, the rule body is matched against the base graph. || `rule.id` | An identifier for the rule, which is a blank node or iri. |
| `filter.expr` | The expression of a filter element |
| `assign.var` | The assignment variable of the [assignment element]. |
| `assign.expr` | The assignment expression |
| `negation.inner` | The negation element body is a negation element. |
| `negation.data` | A boolean flag; if false, the `negation.inner` is matched against the base graph. |

### 4.2 Well-formedness Conditions

*Well-formedness* is a set of conditions on the abstract syntax of
a rule set. Together, these conditions ensure
that a variable in the
head of a rule has a value defined in the body of the rule;
that each variable in a filter element
or assignment expression
has a value at the point of evaluation;
and that each
assignment in a rule introduces a new variable,
one that has not been used earlier in the rule body.

We define *well-formedness* for a sequence of rule elements
given an initial set of variables.

Let elti be the i-th element of a sequence of rule elements.

Let varsi be the set of variables defined by
elti where:

- If elti is a triple pattern element then
  - varsi is the set of variables
    that occurs in the triple pattern element.
- If elti is a assignment element then
  - varsi is the set of the assignment variable.
- Otherwise,
  - varsi is the empty set.

Let V0 be the initial variables of a sequence.

Let Vi
be the union of V0 and all varsj,
where j is less than i.

Let Vall be VN
where N is the length of the sequence.

A well-formed sequence is a sequence of rule elements,
given a set of variables V0,
if the following conditions are met:

- If elti is a filter element then
  - every variable mentioned in a filter element
    is an element of Vi-1.
- If elti is a assignment element then
  - every variable mentioned in the assignment expression
    is an element of Vi-1
  - the assignment variable is an not element of Vi-1.
- If elti is a negation element then
  - the sequence of rule elements in the
    negation element body is a well-formed sequence
    given the set of variables Vi-1.

A rule is a well-formed rule
if the sequence of the rule body is a well-formed sequence given
V0 is the empty set,
and each variable in a triple template of the rule head
is an element of Vall.

A rule set is a well-formed rule set if and only if all
rules of the rule set are well-formed rules.

### 4.3 Rule Dependency

A rule `R1` depends on a rule `R2` if the output of the second rule
affects the evaluation of the body of the first rule. That is, the head of `R2`
has a triple template that might generate a triple that matches
a triple pattern in the body of `R1`,
either as a triple pattern element or inside a negation element.

There are two kinds of dependency:
closed dependencies and open dependencies.
A *closed dependency* ensures that rule `R2`
has generated all its possible output before rule `R1` is executed.
If a rule dependency is not closed, it is an *open dependency*
which allows the first rule `R1` to be executed
while the rule `R2` might be run again to generate further triples
which can then cause `R1` to be reevaluated with the new triples from `R2`.

In this first example, the first rule has an open dependency
on the second rule.

**Example: Open Dependency**

```
            RULE { ?x :exposedTo ?v } WHERE { ?x :dependsOn ?y . ?y :hasVulnerability ?v }
            RULE { ?x :dependsOn ?y } WHERE { ?x :callsService ?y }
```

In this second example, the first rule has a closed dependency
on the second rule: the triple pattern `?x :status :criticallyExposed`
occurs inside a negation element of the first rule and
matches the triple template in the head of the second rule.
The first rule cannot be evaluated until the second rule
has generated all its possible output.

**Example: Closed Dependency**

```
            RULE { ?x :status :safeToDeploy }
            WHERE { ?x rdf:type :Component . NOT { ?x :status :criticallyExposed } }

            RULE { ?x :status :criticallyExposed } WHERE { ?x :exposedTo ?v }
```

Triple pattern matching
:   A triple pattern matches a triple template if
    the triple template can generate a triple that matches the triple pattern.

Triple pattern dependency
:   A triple pattern
    depends on a triple template
    if the triple pattern could possibly match the triple template.

    A triple pattern
    depends on a rule
    if the triple pattern has dependency on any of the triple templates
    in the head of the rule.

Rule dependency
:   Rule `R1` depends on `R2` if any triple pattern in the body of `R1`,
    whether as a triple pattern element or inside a negation element,
    [depends on](#dfn-triple-pattern-dependency)
    a triple template in the head of `R2`.

Closed dependency
:   A rule dependency of rule `R1` on rule `R2` is a closed dependency
    if any of the following conditions hold:

    - A triple pattern occurring inside a negation element of `R1`
      matches a triple template in the rule head of `R2`.
    - Rule `R1` depends on rule `R2`
      and `R1` has an assignment element.
    - Rule `R1` depends on rule `R2`
      and the rule head of `R1` has a blank node.

Open dependency
:   A rule dependency of rule `R1` on rule `R2`
    is an open dependency if the dependencyis not a
    closed dependency.
    That is, any triple pattern of `R1` that depends on
    `R2` occurs only as a triple pattern element.

A triple template can generate an
RDF triple `T1`
if there are values for the variables of the
triple template such that replacing variables by values
in the template, gives a triple `T2` where
`T2` equals `T1`.

Similarly, a triple pattern matches a triple `T1`
if there are values for the variables of the
triple pattern such that replacing variables by values
in the pattern, gives a triple `T2` where
`T2` equals `T1`.
For a triple pattern, this includes
symmetric triples.

If a variable is used more then once in a triple template
or triple pattern, then the same RDF term
is used as the replacement.

Replacing variables by RDF terms including variables inside
triple terms.

#### 4.3.1 Dependency Graph

The dependencies between rules are represented as a directed graph,
called the dependency graph.
The vertices of the graph are the rules of the rule set, and the edges
are labeled either *open* or *closed* according to
whether the dependency is an open dependency or a closed dependency.

Dependency graph
:   A dependency graph of a rule set is a directed graph where each
    vertex is a rule in the rule set, and an edge exists from rule `R1`
    to rule `R2` if `R1` depends on `R2`.
    The edge is labeled either *open*
    or *closed* according whether the dependency
    is an open dependency or a closed dependency.

Transitive rule dependency
:   A rule `R1` has a transitive dependency on rule `R2`
    if there is a path in the dependency graph from `R1` to `R2`.

Recursive rule dependency
:   A rule `R` has a recursive dependency if there is a cyclic path
    in the dependency graph involving `R`.

**Note:** The dependency graph is not affected by the data graph.

#### 4.3.2 Dependency Graph Algorithm

The following algorithm gives one
possible method for constructing the dependency graph from a
rule set. Conformance depends on producing a dependency graph
that meets the definitions of a dependency graph,
not on the use of this procedure.

```
define mergeLabel(oldLabel, newLabel):
    ## Closed dependency overrides open dependency.
    if oldLabel == "open" and newLabel == "open":
        return "open"
    else:
        return "closed"
    endif
enddefine

## output -- Dependency graph with rule vertices and labeled edges.
define buildDependencyGraph(ruleSet):
    ## edgeLabelMap maps (R1, R2) to "open" or "closed"
    let edgeLabelMap be a map from pair (rule, rule) to label

    foreach rule R1 in ruleSet.rules:
        ## Classify each triple pattern TP in the rule as requiring "open" or "closed"
        ## depending on whether it is in a negation element or not.
        let bodyDependencies = {}
        foreach rule element RBE in R1.body:
            if RBE is a negation element:
                foreach triple pattern TP in RBE.inner
                    let item be a pair (TP, "closed")
                    add item to bodyDependencies
                endfor
            else if RBE is a triple pattern element of triple pattern TP:
                let item be a pair (TP, "open")
                add item to bodyDependencies
            else if RBE is a condition element:
                ## Do nothing
            else if RBE is an assignment element:
                ## Do nothing
            endif
        endfor

        foreach pair (triple pattern TP, depLabel) in bodyDependencies:
            if R1.body has an assignment element:
              set depLabel to "closed"
            endif
            if R1.head has a triple template with a blank node:
              set depLabel to "closed"
            endif
            ## Find dependencies for this triple pattern element or negation element.
            foreach rule R2 in ruleSet.rules:
                foreach triple template TT in R2.head:
                    if triple pattern TP matches triple template TT:
                        let key = (R1, R2)
                        if edgeLabelMap contains key:
                            let oldLabel = edgeLabelMap.get(key)
                            let merged = mergeLabel(oldLabel, depLabel)
                            edgeLabelMap.set(key, merged)
                        else:
                            edgeLabelMap.set(key, depLabel)
                        endif
                    endif
                endfor
            endfor
        endfor
    endfor

    let DP = { }
    foreach entry ((R1, R2), label) in edgeLabelMap:
        add an edge (R1 -> R2) labeled with label to DP
    endfor

    the result is DP
    enddefine
```

### 4.4 Stratification

Stratification is the process of partitioning a rule set
into an ordered sequence of stratification layers (also known
as "strata", singular "stratum"). Rules in lower strata are
evaluated before rules in higher strata.

Stratification imposes constraints on dependencies between rules
to ensure that negation elements, assignment elements, and
blank nodes created in a rule head depend only on results computed
using earlier (lower) strata and the base graph.
This guarantees a single, well-defined, and finite
outcome from the evaluation of a rule set over a given base graph.

**Note:** A stratification process may also be used to make other evaluation
decisions. This document describes the necessary conditions for
consistent evaluation and gives one possible way to form a
stratification. Implementations need to meet the conditions
described here in order to get compatible behavior but they are not
required to implement the algorithm as presented.

Stratification layer
:   A stratification layer `SL`, is a pair of disjoint sets of
    rules (`SL.once`, `SL.general`) .
    `SL.once` contains run-once rules, which are
    rules that use assignment elements or produce
    blank nodes in the rule head; these rules are each evaluated exactly
    once at the start of evaluation of the stratification layer.
    `SL.general` contains the remaining rules, which are evaluated
    repeatedly until no new triples are inferred.

Stratification
:   A stratification of a rule set is a sequence of stratification layers.
    Each rule in a rule set appears in exactly one of the sets of one of
    the stratification layers.

#### 4.4.1 Stratification Condition

Stratification is only defined when the following condition is
satisfied. If a rule set does not meet this condition, then this
specification does not define an outcome for the evaluation of
such a rule set.

Stratification Condition
:   The stratification condition requires that
    there is no recursive dependency involving a
    closed dependency
    in the dependency graph for a rule set.

In other words, there is no `NOT` or run-once rule (assignment or rule triple template
involving a blank node) in any transitive dependency cycle of the dependency graph.

#### 4.4.2 Stratification Algorithm

The following algorithm gives one possible stratification based solely
on the rule set.

```
## output -- Map: Integer -> Set of rules.

define stratification(ruleSet):

    let DP = Dependency graph for the rule set.
    let stratumMap be a map from rule to integer

    ## The dependency graph should satisfy the stratification condition.
    ## The check for unbounded stratification is a guard 
    ## due to a violation of the stratification condition.
    let limit = num rules + 1
    let maxStratum = 0

    ## initialize stratumMap
    foreach rule in ruleSet.rules:
        stratumMap.set(rule, 0)
        endfor

    boolean changed = true;
    while changed:
        changed = false;
        foreach edge E in DP:
            ## Edge from pRule to qRule with a label
            let pRule = source of edge
            let qRule = destination of the edge
            let label = edge label

            if label == "open" :
                if stratumMap.get(pRule) < stratumMap.get(qRule) :
                    stratumMap.set(pRule, stratumMap.get(qRule))
                    changed = true;
                endif
            endif
            if label == "closed" :
                if stratumMap.get(pRule) <= stratumMap.get(qRule) :
                    let xStratum = 1 + stratumMap.get(qRule)
                    if ( xStratum > limit )
                        ## Stratification requirement violated
                        error "Stratification error"
                        endif
                    stratumMap.set(pRule, xStratum)
                    maxStratum = max(maxStratum, xStratum)
                    changed = true;
                endif
            endif
        endfor
    endwhile

    ## Initialize the result map.
    let stratumRules be a map from integer to rules.
    for i = 0 to maxStratum
        stratumRules.set(i, {})
    endfor

    ## Gather rules in stratumMap with the same level number
    for rule R in map stratumMap:
        let stratumNum = stratumMap.get(R)
        add R to stratumRules.get(stratumNum)
    endfor

    ## Partition each level into once and general
    let stratumLevels be a sequence of pairs of sets of rules.
    for i = 0 to maxStratum:
        let rules = stratumRules.get(i)
        let once = { R in rules | R is a run-once rule }
        let general = rules \ once
        stratumLevels.set(i, pair(once, general))
    endfor

    the result is stratumLevels
enddefine
```

**Note:** A consequence of the stratification condition is that once a
run-once rule is [evaluated](#eval-rule),
the data used to determine the outcome of the rule will not
change during further evaluation.

A step-by-step application of dependency analysis and
stratification to a complete rule set, followed through to
evaluation, is given in
[6.6 Worked Example](#eval-worked-example).

### 4.5 Processing Imports

Reading documents from the web has security implications.
Support for importing rule sets is optional for SRL processors.
Further, implementations MAY provide partial support,
such as supporting imports of certain rules sets and not others,
and possibly from a verified copy.

The following condition apply to imports processing:

- Implementations that do not support importing rule sets MUST reject
  a rule sets that contain `IMPORTS` statements and signal an error.
- An implementation that provides partial support
  MUST signal an error if it encounters an import
  that it does not support.
- An implementation MUST signal an error if it can not resolve the import document,
  or if the document is not syntactically valid.
- Processors MUST only import a rule set once to avoid infinite loops
  when processing `IMPORTS` statements.

A resolved rule set is produced from another rule set by
recursively reading all rule sets mentioned
in the imports of that other rule set.

An example algorithm is provided in [A. Example Imports Algorithm](#alg-imports).

## 5. Concrete Syntax forms for the Shape Rules Language

There are two concrete syntaxes.

- [Shape Rules Language syntax](#shape-rules-syntax)
- [RDF Rule syntax](#rdf-rules-syntax)

The Shape Rules Language (SRL) syntax has an equivalent RDF syntax form.
Well-formed RDF syntax can be translated to the Shape Rules Language syntax.

Shape Rules Language:

**Example: Example of SRL/text**

```
          PREFIX : <http://example/>

          DATA { :x :p 1 ; :q 2 . }

          RULE { ?x :bothPositive true . }
          WHERE { ?x :p ?v1  FILTER ( ?v1 > 0 )  ?x :q ?v2  FILTER ( ?v2 > 0 )  }

          RULE { ?x :oneIsZero true . }
          WHERE { ?x :p ?v1 ;  :q ?v2  FILTER ( ( ?v1 = 0 ) || ( ?v2 = 0 ) )  }
```

RDF Rules syntax:

**Example: SHACL Rules in RDF**

```
PREFIX :       <http://example/>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX srl:    <http://www.w3.org/ns/shacl-rules#>
PREFIX sparql: <http://www.w3.org/ns/sparql#>

:ruleSet-1
  rdf:type srl:RuleSet ;
  srl:data (
    [  srl:subject :x  ; srl:predicate :p  ; srl:object 1 ]
    [  srl:subject :x  ; srl:predicate :q  ; srl:object 2 ]
  ) ;
  srl:rules (
    [
      rdf:type srl:Rule ;
      srl:body (
        [
          srl:triplePattern [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :p ;
            srl:object [ srl:varName "v1" ]
          ]
        ]
        [
          srl:filter [
            sparql:greater-than ( [ srl:varName "v1" ] 0 )
          ]
        ]
        [
          srl:triplePattern [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :q ;
            srl:object [ srl:varName "v2" ] ;
          ]
        ]
        [
          srl:filter [
            sparql:greater-than ( [ srl:varName "v2" ] 0 )
          ]
        ]
      ) ;
      srl:head (
        [
          srl:tripleTemplate [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :bothPositive ;
            srl:object true
          ]
        ]
      )
    ]
    [
      rdf:type srl:Rule ;
      srl:body (
        [
          srl:triplePattern [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :p ;
            srl:object [ srl:varName "v1" ] ;
          ]
        ]
        [
          srl:triplePattern [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :q ;
            srl:object [ srl:varName "v2" ] ;
          ]
        ]
        [
          srl:filter [
            sparql:logical-or (
              [ sparql:equals ( [ srl:varName "v1" ] 0 ) ]
              [ sparql:equals ( [ srl:varName "v2" ] 0 ) ]
            )
          ]
        ]
      ) ;
      srl:head (
        [
          srl:tripleTemplate [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :oneIsZero ;
            srl:object true ;
          ]
        ]
      )
    ]
  ) .
```

### 5.1 Shape Rules Language syntax

The [grammar](#shapes-rules-grammar) is given below.

Mapping the AST to the abstract syntax.

### 5.2 RDF Rules Syntax

Vocabulary: [rdf-syntax-vocab.ttl](./rules-rdf-syntax/rdf-syntax-vocab.ttl)
  
SHACL shapes: [rdf-syntax-shapes.ttl](./rules-rdf-syntax/rdf-syntax-shapes.ttl)

Well-formedness:

- All RDF lists are well-formed
- exactly one of subject - predicate - object, per body of head
  element
- Well-formed, single-valued,list-argument node expressions
- well-formed abstract syntax

Describe how the abstract model maps to triples.

Process : accumulators, bottom up/ Walk the structure.

- Collect data triples
- Map expressions
- Map triple-patterns
- Map triple-templates
- Map assignments
- Map to rule
- Rule set

All triples not in the syntax are ignored.
No other "srl:" predicates are allowed (??).

@@ Illustration: SHACL rule set in text and RDF syntaxes: all features:

```
DATA { :s :p :o }
RULE { ?x :q :o } WHERE { ?x :p :o }
RULE { ?x :q ?o } WHERE { ?x :p :o . SET (?o := 18) }
RULE { ?x :q ?o } WHERE { ?x :p :o . NOT { ?s :p ?o . FILTER(?o > 18) } }
```

```
PREFIX :       <http://example/>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX sparql: <http://www.w3.org/ns/sparql#>
PREFIX srl:    <http://www.w3.org/ns/shacl-rules#>

:ruleSet-features
  rdf:type srl:RuleSet ;
  srl:data (
    [
      srl:subject :s ;
      srl:predicate :p ;
      srl:object :o
    ]
  ) ;
  srl:rules (
    [
      rdf:type srl:Rule ;
      srl:head (
        [
          srl:tripleTemplate [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :q ;
            srl:object [ srl:varName "o" ]
          ]
        ]
      )
      srl:body (
        [
          srl:triplePattern [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :p ;
            srl:object :o
          ]
        ]
      ) ;
      srl:head (
        [
          srl:tripleTemplate [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :q ;
            srl:object :o
          ]
        ]
      )
    ]
    [
      rdf:type srl:Rule ;
      srl:body (
        [
          srl:triplePattern [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :p ;
            srl:object :o
          ]
        ]
        [
          srl:assign [
            srl:assignValue 18 ;
            srl:assignVar [ srl:varName "o" ]
          ]
        ]
      ) ;
    ]
    [
      rdf:type srl:Rule ;
      srl:head (
        [
          srl:tripleTemplate [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :q ;
            srl:object [ srl:varName "o" ]
          ]
        ]
      )
      srl:body (
        [
          srl:triplePattern [
            srl:subject [ srl:varName "x" ] ;
            srl:predicate :p ;
            srl:object :o ;
          ]
        ]
        [
          srl:not (
            [
              srl:triplePattern [
                srl:subject [ srl:varName "s" ] ;
                srl:predicate :p ;
                srl:object [ srl:varName "o" ]
              ]
            ]
            [
              srl:filter [
                sparql:greater-than ( [ srl:varName "o" ] 18 )
                )
              ]
            ]
          )
        ]
      ) ;
    ]
  ) .
```

### 5.3 Version Announcement

A version label is a string that identifies the syntax and semantics conformance
for the Shape Rules Language.

Version Labels

| Version Label |
| --- |
| "1.2" |

The version announcement SHOULD be made early in the document.

Multiple [`VERSION`](#rVersionDecl) directives
may appear in a SPARQL-RL Document.
Each directive applies to the part of the document following the directive,
until another directive is encountered or the end of the document is reached.

Version labels can also be given by the `version` parameter of the
[Media Type](#media-type). In the absence of a current
[`VERSION`](#rVersionDecl) directive, the
version specified as part of the Media Type is considered.

## 6. Rule Set Evaluation

This section defines the outcome of evaluating a rule set on given data.
It does not prescribe the algorithm as the method of implementation.
An implementation can use any algorithm that generates the same outcome.

```
Inputs: data graph G, called the base graph, and a rule set RS.
Output: an RDF graph GI of inferred triples
```

The inferred triples do not include triples present in the set
of triples of the base graph.

### 6.1 Evaluation Definitions

Solution mapping
:   A solution mapping, μ, is a partial function
    `μ : V → T`,
    where V is the set of all variables
    and T is the set of all RDF terms.
    The domain of μ is denoted
    by `dom(μ)`, and it is the subset
    of V for which μ is defined. We use the term
    solution where it is clear that a solution mapping is meant.
    Write μ0 for the solution mapping, such that
    `dom(μ0)` is the empty set.

Substitution function
:   A substitution function, or just a *substitution*,
    is a function
    `subst(μ, triple pattern)`
    that returns a triple pattern
    where each occurrence in the triple pattern of a variable that is in the
    `dom(μ)`
    is replaced by the RDF term given by the
    solution mapping for var.
    If the triple pattern result has no variables, then it is an RDF Triple.

Evaluation graph
:   A evaluation graph is an RDF Graph that combines the base graph
    and all triples produced during the evaluation of a rule set.

Graph match
:   A graph match finds the ways to
    map a triple pattern onto triples in an RDF Graph.

    Let G be an RDF graph and TP be a triple pattern.
    The function `graphMatch(G, TP)` returns a set of all possible
    solutions that,
    when applied to the triple pattern, produce a triple that is in the
    evaluation graph

    Let G be an RDF graph, TP be a triple pattern,
    and V be the set of variables occuring in TP.

    ```
    graphMatch(G, TP) = { μ | dom(μ) = V and subst(μ, TP) is a triple in G }
    ```

Solution compatible
:   Two solutions S1 and S2 are compatible if they agree on the variables in common.

    Let S1 and S2 be solutions.

    ```
    compatible(μ1, μ2) = true
                          if forall v in dom(μ1) intersection dom(μ2)
                              μ1(v) = μ2(v)
    compatible(μ1, μ2) = false otherwise
    ```

Solution sequence
:   A solution sequence is a multi-set of solutions.
    There is no defined order to the sequence.
    It is equivalent to an unordered list and it can contain duplicates.

Solution merge
:   If two solutions are compatible, the merge of two solutions is the solution
    that maps variables of each solution to the RDF term
    from one or other of the solutions.

    Let μ1, μ2
    be solution mappings, and S1 and S2 be solution sequences.

    ```
    merge(μ1, μ2) = { μ |
                        μ(v) = μ1(v) if v in dom(μ1)
                        μ(v) = μ2(v) otherwise }
    ```

    ```
    merge(S1, S2) = { μ |
                        μ1 in S1, μ2 in S2
                        and compatible(μ1, μ2)
                        μ(v) = merge(μ1, μ2) }
    ```

    **Note:** The domain of `merge(S1, S2)` is `domain(S1) ∪︀ domain(S2)`

    If the two solutions have no variables in common, then they are compatible,
    and the merge of the two solutions is the union of the `S1` and `S2`.

Effective boolean value
:   The function `EBV(x)` returns the effective boolean value
    for an RDF term.

### 6.2 Preparation for Evaluation

Evaluation of a rule set involves collecting all imported rule sets,
building a single, combined rule set as described in
[4.5 Processing Imports](#process-imports).

Then preparing the combined rule set
for evaluation with the following steps.

1. Check each rule is a well-formed rule, as described in
   [4.2 Well-formedness Conditions](#wellformed).
2. Calculate the dependency graph, as described in
   [4.3.2 Dependency Graph Algorithm](#dependency-graph-construction-algorithm).
3. Calculate the stratification for the combined rule set, as described in
   [4.4.2 Stratification Algorithm](#stratification-algorithm)).

### 6.3 Evaluation of an Expression

An expression, whether used in a filter element or
an assignment element, is evaluated with
respect to a solution mapping which provides a value which is an RDF term,
for each variable in the expression.
The well-formedness requirements of [4.2 Well-formedness Conditions](#wellformed)
ensure that all variables in the expression
appear in the solution mapping.

```
define evalFunction(F, μ):
    ## F is an expression: an RDF term, a variable, or op(expr1, ..., exprN)
    ## where op is a function or a functional form.
    if F is an RDF term:
        return F
    if F is a variable:
        ## By well-formedness, F ∈ dom(μ).
        return μ(F)
    ## F is of the form F= op(expr1, ..., exprN)
    if op is a functional form (e.g. IF, logical-or):
        ## Evaluated specifically for op; op may evaluate only some arguments.
        ## For example, IF(c, t, f) evaluates c, then exactly one of t or f.
        return the value defined for op over expr1, ..., exprN under μ
    ## op is an ordinary function: evaluate all arguments first.
    return F(evalFunction(expr1, row), ..., evalFunction(exprN, row))
enddefine
```

### 6.4 Evaluation of a Rule

A rule is evaluated by calculating a solution sequence from the rule body
and then using each solution mapping of the solution sequence to
generate triples using rule head.

Blank nodes within triple patterns behave like variables.
This is compatible with
SPARQL graph pattern matching.

```
let R be a well-formed rule

let B be R.body 
  where each blank node in a triple pattern in R.body
  is replaced by a variable which is not used in the rule. 
  The same variable is used for each occurrence of the
  same blank node, and a different variable is used for 
  different blank nodes.

# Solution sequence of one solution that does not map any variables.
let SEQ0: Solution sequence = { μ0 }

let G = evaluation graph

# Evaluate rule body
# This function returns a sequence of solutions
define evalRuleElements(B, SEQ, G, GD):
    where 
      B is a sequence of rule elements
      SEQ is a solution sequence 
      G and GD are RDF graphs

    for each rule element rElt in B:

        if rElt is a triple pattern TP:
            X = graphMatch(G, TP)
            SEQ1 = {}
            for each μ1 in X:
                for each μ2 in SEQ:
                    if compatible(μ1, μ2)
                      μ3 = merge(μ1, μ2)
                      add μ3 to SEQ1
                    endif
                endfor
            endfor
        endif

        if rElt is a condition element F:
            SEQ1 = {}
            for each solution μ in SEQ:
                let x = evalFunction(F.expr, μ)
                if EBV(x) is true:
                    add μ to SEQ1
                endif
            endfor
        endif

        if rElt is a negation expression N:
            SEQ1 = {}
            for each solution μ in SEQ:
                S = sequence{ μ }
                if rElt with DATA:
                    NEG = evalRuleElements(N.inner, S, GD, GD)
                else:
                    NEG = evalRuleElements(N.inner, S, G, GD)
                if NEG is empty
                    add μ to SEQ1
                endif
            endfor
        endif

        if rElt is an assignment A:
            SEQ1 = {}
            for each solution μ in SEQ:
                let x = evalFunction(A.expr, μ)
                if x is not an error:
                    ## Add mapping V -> x to solution μ
                    let μ2 be a solution mapping μ ∪︀ { (A.var, x) }
                    add μ2 to SEQ1
                else
                    # Error: drop solution μ
                endif
            endfor
        endif

        SEQ = SEQ1
    endfor

    return SEQ
enddefine

if R.data:
    ## Rule WHERE DATA
    let SEQ = evalRuleElements(R, SEQ0, GD, GD)
else
    let SEQ = evalRuleElements(R, SEQ0, G, GD)

# Evaluate rule head
let OUT = empty set
for each μ in SEQ:
    let S = {}
    for each triple template TT in R.head:
        let triple = subst(μ, TT)
        Add triple to S
    endfor
    OUT = OUT union S
endfor

result evalRule(R, G, GD) is OUT
```

**Note:** `OUT` may contain triples that are also in the data graph.

### 6.5 Evaluation of a Rule Set

Evaluation of a rule set is defined as the execution of each stratum of the
stratification of the rule set, where each stratum is executed completely
and in order before moving on to the next stratum.
A stratum is evaluated by first evaluating
each of the run-once rules of that stratum, and then evaluating
general rules of the stratum repeatedly until no new triples are produced.

```
let G0 be the input base graph
let RS be the rule set
let D be the graph of all DATA triples in RS

Apply stratification to RS

let LS be the sequence of layers after stratification

# Inference graph
let GI = { t ∈ D | t ∉ G0 }

let GD = G0 ∪︀ D

# Evaluation graph.
let GE = GD

for each stratum ST in LS:
    for each rule R in ST.once:
        let X = evalRule(R, GE, GD)
        let Y = { t ∈ X | t ∉ GE }
        GI = Y ∪︀ GI
        GE = Y ∪︀ GE
    endfor

    let finished = false
    while !finished:
        finished = true
        for each rule R in ST.general:
            let X = evalRule(R, GE, GD)
            let Y = { t ∈ X | t ∉ GE }
            if Y is not empty:
                finished = false
                GI = Y ∪︀ GI
                GE = Y ∪︀ GE
            endif
        endfor
    endwhile
endfor
the result is GI
```

### 6.6 Worked Example

This section steps through the evaluation of a complete
rule set: determining the rule dependencies
([4.3 Rule Dependency](#rule-dependency)),
calculating a stratification
([4.4 Stratification](#stratification)),
and evaluating each stratum in turn to produce the
inference graph
([6.5 Evaluation of a Rule Set](#eval-rule-set)).

The example describes software components and their dependencies:
a frontend depends on an application server, which depends on a
database and on a logging library. The database has a known
vulnerability. The rules propagate exposure to vulnerabilities
along the dependency chain, give components exposed to a severe
vulnerability the status `:criticallyExposed`, give components that are
not critical the status `:safeToDeploy`, and create a
notification for each critically exposed component.
(In practice, whether a vulnerability affects a component
depends on the deployed version; the example elides versions and
states the vulnerability directly.)
For brevity, the base graph states `:dependsOn` triples directly,
rather than deriving them from more specific relations as in
[3.1 Basic Patterns](#desc-basic).

**Example: Worked example: data and rules**

```
            :frontend rdf:type :Component ;
                      :dependsOn :app .
            :app      rdf:type :Component ;
                      :dependsOn :db ;
                      :dependsOn :logger .
            :db       rdf:type :Component ;
                      :hasVulnerability :vuln1 .
            :logger   rdf:type :Component .
            :vuln1    :severity 9.1 .
```

```
            # R1
            RULE { ?x :exposedTo ?v } WHERE { ?x :hasVulnerability ?v }

            # R2
            RULE { ?x :exposedTo ?v } WHERE { ?x :dependsOn ?y . ?y :exposedTo ?v }

            # R3
            RULE { ?x :status :criticallyExposed }
            WHERE { ?x :exposedTo ?v . ?v :severity ?s . FILTER(?s >= 9.0) }

            # R4
            RULE { ?x :status :safeToDeploy }
            WHERE { ?x rdf:type :Component . NOT { ?x :status :criticallyExposed } }

            # R5
            RULE { [] rdf:type :Notification ; :concerns ?x }
            WHERE { ?x :status :criticallyExposed }
```

The rules are labeled `R1` to `R5` in comments and are referred
to by these labels in the rest of this section.
They are the rules introduced in
[3.2 Recursion](#desc-recursion) through
[3.5 Assignment and Creating RDF Terms](#desc-creating-rdf-terms).
The rule set has no `IMPORTS`, so import processing
leaves it unchanged, and no `DATA` blocks, so evaluation starts
from the base graph alone.

#### 6.6.1 Determining the Dependencies

Each triple pattern in each rule body is compared with the
triple templates in every rule head, to determine which rules
depend on which
([4.3 Rule Dependency](#rule-dependency)).

- The body of `R1` is the single triple pattern
  `?x :hasVulnerability ?v`. No rule head has a triple template
  that can generate a triple with predicate `:hasVulnerability`,
  so this pattern can only match the data.
  `R1` has no dependencies.
- The body of `R2` has two triple patterns.
  `?x :dependsOn ?y` cannot match any rule head, so it matches
  only the data. `?y :exposedTo ?v` matches the head template
  `?x :exposedTo ?v` of `R1`, and also matches the head of `R2`
  itself. Both occurrences are triple pattern elements
  (they do not occur inside a negation element, and `R2` has
  no assignment element and no blank node in its head), so
  `R2` has an *open* dependency on `R1` and an
  *open* dependency on itself.
  The dependency of `R2` on itself makes `R2` a recursive rule.
- In the body of `R3`, the pattern `?x :exposedTo ?v` matches
  the heads of `R1` and `R2`, giving `R3` an *open*
  dependency on each. The pattern `?v :severity ?s` matches no
  rule head.
- In the body of `R4`, the pattern `?x rdf:type :Component`
  matches no rule head: the only head template with predicate
  `rdf:type` is in `R5`, and its object `:Notification` is
  a different RDF term from `:Component`, so no generated
  triple can match.
  The pattern `?x :status :criticallyExposed` occurs inside the
  negation element `NOT { ?x :status :criticallyExposed }` and
  matches the head template of `R3`. Because the pattern
  occurs in a negation element, `R4` has a *closed*
  dependency on `R3`.
- In the body of `R5`, the pattern `?x :status :criticallyExposed`
  matches the head of `R3`. The head of `R5` contains a
  blank node, so its dependency on `R3` is a *closed*
  dependency, even though the pattern is an ordinary
  triple pattern element.
  No pattern in any rule body matches the head templates of
  `R5`, so no rule depends on `R5`.

The dependency graph therefore has five vertices and six
edges:

- `R2 → R1` (open)
- `R2 → R2` (open)
- `R3 → R1` (open)
- `R3 → R2` (open)
- `R4 → R3` (closed)
- `R5 → R3` (closed)

Although `R4` and `R5` have no direct dependency on `R1` or
`R2`, each has a transitive dependency on both, through
`R3`.

*[Diagram omitted: Dependency graph of the worked example rule set]*

The dependency graph of the worked example rule set.
Open dependencies are drawn as dashed arrows and closed
dependencies as solid arrows. Each edge points from the
rule whose body contains the matching triple pattern to the
rule whose head could generate the matching triples.
Rules are arranged with stratum 0 at the top and higher
strata below, matching the order of evaluation.

The only cycle in the graph is the self-edge `R2 → R2`,
which is an open dependency. No cycle involves a closed
dependency, so the stratification condition is satisfied
and the rule set has a well-defined outcome.

#### 6.6.2 Calculating the Stratification

Following the
[stratification algorithm](#stratification-algorithm),
every rule starts in stratum 0. The edges are then inspected
repeatedly until nothing changes:

- An *open* edge requires the source rule to be in the
  same stratum as its target or higher. All four open edges
  already satisfy this with every rule at stratum 0, so they
  cause no changes.
- A *closed* edge requires the source rule to be in a
  strictly higher stratum than its target, because the target
  must run to completion first. The edge `R4 → R3`
  (closed) finds `R4` and `R3` both at stratum 0, so `R4` is
  moved to stratum 1. Likewise the edge `R5 → R3`
  (closed) moves `R5` to stratum 1.

A further pass over the edges makes no changes, so the strata
are final. Each stratum is then partitioned into
run-once rules and general rules. `R5` has a blank
node in its head, so it is a run-once rule; no other rule
has an assignment element or a blank node in its head.
The stratification is:

- Stratum 0: general `R1`, `R2`, `R3`; no run-once rules
- Stratum 1: run-once `R5`; general `R4`

This ordering captures the intent of the rules in the higher
stratum. Whether a component is safe to deploy, and which
components need a notification, can only be decided after
*all* `:status :criticallyExposed` triples have been derived
— and the rule that derives them, `R3`, completes in the
stratum below, together with the rules `R1` and `R2` that
feed it.

#### 6.6.3 Evaluating the Strata

Evaluation follows the algorithm of
[6.5 Evaluation of a Rule Set](#eval-rule-set).
The evaluation graph `GE` starts as the base graph and the
inference graph `GI` starts empty. Each stratum is evaluated to
completion in order: the rules of the stratum are evaluated in
passes, and passes repeat until a pass produces no new triples.
The algorithm does not fix the order in which the rules of a
stratum are evaluated within a pass; this trace uses the order
`R1`, `R2`, `R3`. A different order can spread the same
inferences across a different number of passes but, because
stratum 0 runs to completion, it produces the same final graph.

Because this rule set has no `DATA` blocks, `GE` is `G0` plus
`GI` at every point in the evaluation. The trace therefore
tracks only `GI`, showing its state as evaluation proceeds and
marking each new triple with the rule that produced it.

**Stratum 0, first pass.**

- `R1`: the body matches
  `:db :hasVulnerability :vuln1`, binding
  `?x = :db` and `?v = :vuln1`.
  The head produces `:db :exposedTo :vuln1`.
  The triple is not in `GE`, so it is added to `GE` and `GI`.
- `R2`: the body joins `?x :dependsOn ?y` with
  `?y :exposedTo ?v`. `GE` now contains
  `:db :exposedTo :vuln1`, so the join yields one solution:
  `?x = :app`, `?y = :db`, and `?v = :vuln1`
  (from `:app :dependsOn :db`).
  The head produces `:app :exposedTo :vuln1`, which is new and
  is added. There is no solution for `:frontend` yet, because
  `:app :exposedTo :vuln1` was not in `GE` when this
  evaluation of `R2` started.
- `R3`: `?x :exposedTo ?v` now matches for `:db` and `:app`;
  joining with `:vuln1 :severity 9.1` and applying
  `FILTER(?s >= 9.0)` keeps both solutions.
  The head produces `:db :status :criticallyExposed` and
  `:app :status :criticallyExposed`, both new.

```
            # GI after stratum 0, first pass
            :db  :exposedTo :vuln1 .                    # new (R1)
            :app :exposedTo :vuln1 .                    # new (R2)
            :db  :status :criticallyExposed .           # new (R3)
            :app :status :criticallyExposed .           # new (R3)
```

New triples were produced, so evaluation of stratum 0
continues with another pass.

**Stratum 0, second pass.**

- `R1`: matches as before; `:db :exposedTo :vuln1` is already
  in `GE`, so nothing new is produced.
- `R2`: the join now also yields
  `?x = :frontend`, `?y = :app`, and `?v = :vuln1`, producing
  the new triple `:frontend :exposedTo :vuln1`.
  The exposure has taken two passes to travel two steps along
  the dependency chain.
- `R3`: produces the new triple
  `:frontend :status :criticallyExposed`.

```
            # GI after stratum 0, second pass
            :db       :exposedTo :vuln1 .
            :app      :exposedTo :vuln1 .
            :frontend :exposedTo :vuln1 .               # new (R2)
            :db       :status :criticallyExposed .
            :app      :status :criticallyExposed .
            :frontend :status :criticallyExposed .      # new (R3)
```

**Stratum 0, third pass.**
Every solution of every rule now produces only triples already
in `GE`. `GI` is unchanged.
No new triples means stratum 0 is complete: every
`:exposedTo` triple and every `:status :criticallyExposed` triple that
can ever be derived has been derived.

**Stratum 1, run-once rules.**
The run-once rules of the stratum are evaluated first,
each exactly once.

- `R5`: the body matches the three `:status :criticallyExposed`
  triples, giving the solutions `?x = :db`, `?x = :app`, and
  `?x = :frontend`. For each solution, instantiating the head
  creates a *fresh* blank node, producing two triples
  per solution: a notification for each critical
  component. `R5` is not evaluated again, even though the
  general rules of the stratum will now be evaluated
  repeatedly.

**Stratum 1, first pass of the general rules.**

- `R4`: the pattern `?x rdf:type :Component` matches
  `:frontend`, `:app`, `:db`, and `:logger`.
  (It does not match the `rdf:type :Notification` triples
  just created by `R5`.)
  The negation element `NOT { ?x :status :criticallyExposed }` rejects
  the solutions for `:frontend`, `:app`, and `:db`, because
  `GE` contains a `:status :criticallyExposed` triple for each of them.
  Only the solution `?x = :logger` survives, producing the new
  triple `:logger :status :safeToDeploy`.

```
            # GI after stratum 1
            :db       :exposedTo :vuln1 .
            :app      :exposedTo :vuln1 .
            :frontend :exposedTo :vuln1 .
            :db       :status :criticallyExposed .
            :app      :status :criticallyExposed .
            :frontend :status :criticallyExposed .
            _:n1      rdf:type :Notification .          # new (R5)
            _:n1      :concerns :db .                   # new (R5)
            _:n2      rdf:type :Notification .          # new (R5)
            _:n2      :concerns :app .                  # new (R5)
            _:n3      rdf:type :Notification .          # new (R5)
            _:n3      :concerns :frontend .             # new (R5)
            :logger   :status :safeToDeploy .           # new (R4)
```

**Stratum 1, second pass of the general rules.**
No new triples. Evaluation is complete, and `GI` as shown
above is the resulting inference graph.

The stratification is what makes this outcome reliable.
Evaluated during the first pass of stratum 0, before
`:frontend :status :criticallyExposed` was derived, `R4` would have
incorrectly concluded `:frontend :status :safeToDeploy`, and
`R5` would have created notifications for `:db` and `:app`
but none for `:frontend`.
Deferring both to stratum 1 means they see the complete set of
`:status :criticallyExposed` triples, so the order in which
rules are evaluated within each stratum does not affect the
final outcome.

## 7. Shape Rules Language Grammar

A SPARQL-RL Document
is an RDF string
encoded in UTF-8 RFC3629 and starting with the
[`RuleSet`](#rRuleSet)
production and conforming to the additional constraints defined in
[7.5 Grammar](#grammar).
Only Unicode scalar values,
in the ranges `U+0000` to `U+D7FF`
and `U+E000` to `U+10FFFF`,
are allowed. This excludes
surrogate code points,
range `U+D800` to `U+DFFF`.

### 7.1 White Space

White space
(production [`WS`](#rWS)) is used
to separate two terminals which would otherwise be (mis-)recognized as one
terminal. Rule names below in capitals indicate where white space is
significant; these form a possible choice of terminals for constructing a
Shape Rules Language parser.

White space is significant in the production
[`String`](#rString).

### 7.2 Comments

Comments start with a [`#`](#cp-number-sign) outside an
[`IRIREF`](#rIRIREF),
[`STRING_LITERAL1`](#rSTRING_LITERAL1),
[`STRING_LITERAL2`](#rSTRING_LITERAL2),
[`STRING_LITERAL_LONG1`](#rSTRING_LITERAL_LONG1), or
[`STRING_LITERAL_LONG2`](#rSTRING_LITERAL_LONG2),
and continue to the end of line (marked by
[`LF`](#cp-line-feed), or
[`CR`](#cp-carriage-return)),
or end of file if there is no end of line after the comment marker.
Comments are treated as white space.

### 7.3 IRI References

Relative IRI references are resolved with base IRIs
as per RFC3986 using only the basic algorithm in section 5.2.
Neither Syntax-Based Normalization nor Scheme-Based Normalization
(described in sections 6.2.2 and 6.2.3 of RFC3986) are performed.
Characters additionally allowed in IRI references are treated in the same way that
unreserved characters are treated in URI references, per section 6.5 of RFC3987.

The [`BASE`](#rBaseDecl)
directive defines the Base IRI used to
resolve relative IRI
references per RFC3986
section 5.1.1, "Base URI Embedded in Content".
Section 5.1.2, "Base URI from the Encapsulating Entity"
defines how the In-Scope Base IRI may come from an encapsulating document,
such as a SOAP envelope with an `xml:base` directive or a MIME multipart document with a
`Content-Location` header.
The "Retrieval URI" identified in 5.1.3, Base "URI from the Retrieval URI",
is the URL from which a particular SPARQL-RL document was retrieved.
If none of the above specifies the Base URI, the default
Base URI (section 5.1.4, "Default Base URI") is used.
Each [`BASE`](#rBaseDecl) directive sets a new In-Scope Base URI,
relative to the previous one.

### 7.4 Escape Sequences

There are three forms of escapes used in
[SRL documents](#dfn-srl-document):

- A numeric escape sequence represents the value of
  a Unicode code point.

  A numeric escape sequence MUST NOT produce a code point value
  in the range `U+D800` to `U+DFFF`,
  which is the range for
  Unicode surrogates.

  | Escape sequence | Unicode code point |
  | --- | --- |
  | `\u` [`hex`](#rHEX) [`hex`](#rHEX) [`hex`](#rHEX) [`hex`](#rHEX) | A Unicode code point in the ranges `U+0000` to `U+D7FF` and `U+E000` to `U+FFFF`, corresponding to the value encoded by the four hexadecimal digits interpreted from most significant to least significant digit. |
  | `\U` [`hex`](#rHEX) [`hex`](#rHEX) [`hex`](#rHEX) [`hex`](#rHEX) [`hex`](#rHEX) [`hex`](#rHEX) [`hex`](#rHEX) [`hex`](#rHEX) | A Unicode code point in the ranges `U+0000` to `U+D7FF` and `U+E000` to `U+10FFFF`, corresponding to the value encoded by the eight hexadecimal digits interpreted from most significant to least significant digit. |

  where [`hex`](#rHEX) is a hexadecimal character

  `HEX ::= [0-9] | [A-F] | [a-f]`
- A string escape sequence represents a character traditionally escaped in string literals:

  | Escape sequence | Unicode code point |
  | --- | --- |
  | `\t` | `U+0009` |
  | `\b` | `U+0008` |
  | `\n` | `U+000A` |
  | `\r` | `U+000D` |
  | `\f` | `U+000C` |
  | `\"` | `U+0022` |
  | `\'` | `U+0027` |
  | `\\` | `U+005C` |
- A reserved character escape sequence consists of a
  [`\`](#cp-backslash) followed by
  one of these characters `~.-!$&'()*+,;=/?#@%_`, and
  represents the character to the right of
  the [`\`](#cp-backslash).

Context where each kind of escape sequence can be used

|  | numeric escapes | string escapes | reserved character escapes |
| --- | --- | --- | --- |
| IRIs, used as RDF terms [`PREFIX`](#rPrefixDecl), or [`BASE`](#rBaseDecl) declarations | yes | no | no |
| [local names](#rPN_LOCAL) | no | no | yes |
| Strings | yes | yes | no |

**Note:** %-encoded sequences are in the
[character range for IRIs](#rIRIREF)
and are [explicitly allowed](#rPERCENT) in local names.
These appear as a [`%`](#cp-percent-sign)
followed by two hex characters and represent that
same sequence of three characters. These sequences are *not*
decoded during processing.
A term written as `<http://a.example/%66oo-bar>`
designates the IRI `http://a.example/%66oo-bar`
and not IRI `http://a.example/foo-bar`.
A term written as `ex:%66oo-bar` with a prefix
`PREFIX ex: <http://a.example/>`
also designates the IRI `http://a.example/%66oo-bar`.

### 7.5 Grammar

The EBNF used here is defined in XML 1.0
EBNF-NOTATION.

Notes:

1. The entry point of the grammar is [`RuleSet`](#rRuleSet).
2. Keywords are case-insensitive except for
   '`a`'
   which is case-sensitive.
3. Escape sequences [`UCHAR`](#rUCHAR)
   and [`ECHAR`](#rECHAR)
   are case sensitive.
4. Variables are not allowed in a [`DATA`](#rDataTriplesBlock) block.
5. When tokenizing the input and choosing grammar rules, the longest match is chosen.
6. The Shape Rules Language grammar is LL(1) and LALR(1) when the rules with uppercased names
   are used as terminals.

|  |  |  |  |
| --- | --- | --- | --- |
| `[1]` | `RuleSet` | ::= | `RuleOrDataBlock` |
| `[2]` | `RuleOrDataBlock` | ::= | `Prologue ( RuleOrData+ ( Prologue1 RuleOrData? )* )?` |
| `[3]` | `RuleOrData` | ::= | `Rule | Data` |
| `[4]` | `Prologue` | ::= | `Prologue1*` |
| `[5]` | `Prologue1` | ::= | `BaseDecl | PrefixDecl | VersionDecl | ImportsDecl` |
| `[6]` | `BaseDecl` | ::= | `'BASE' IRIREF` |
| `[7]` | `PrefixDecl` | ::= | `'PREFIX' PNAME_NS IRIREF` |
| `[8]` | `VersionDecl` | ::= | `'VERSION' VersionSpecifier` |
| `[9]` | `VersionSpecifier` | ::= | `STRING_LITERAL1 | STRING_LITERAL2` |
| `[10]` | `ImportsDecl` | ::= | `'IMPORTS' iri` |
| `[11]` | `Rule` | ::= | `Rule1 | Rule2` |
| `[12]` | `Rule1` | ::= | `'RULE' iri? HeadTemplate ForClause? 'WHERE' 'DATA'? BodyPattern` |
| `[13]` | `Rule2` | ::= | `'IF' iri? ForClause? 'DATA'? BodyPattern 'THEN' HeadTemplate` |
| `[14]` | `Data` | ::= | `'DATA' '{' DataTriplesBlock? '}'` |
| `[15]` | `HeadTemplate` | ::= | `'{' HeadTemplateBlock? '}'` |
| `[16]` | `ForClause` | ::= | `'FOR' Var 'IN' iri` |
| `[17]` | `BodyPattern` | ::= | `'{' BodyTriplesBlock? ( BodyNotTriples '.'? BodyTriplesBlock? )* '}'` |
| `[18]` | `BodyNotTriples` | ::= | `Filter | Negation | Assignment` |
| `[19]` | `Filter` | ::= | `'FILTER' Constraint` |
| `[20]` | `Constraint` | ::= | `BrackettedExpression | BuiltInCall | FunctionCall` |
| `[21]` | `FunctionCall` | ::= | `iri ArgList` |
| `[22]` | `ArgList` | ::= | `NIL | '(' Expression ( ',' Expression )* ')'` |
| `[23]` | `ExpressionList` | ::= | `NIL | '(' Expression ( ',' Expression )* ')'` |
| `[24]` | `Negation` | ::= | `'NOT' 'DATA'? '{' BodyBasic '}'` |
| `[25]` | `BodyBasic` | ::= | `BodyTriplesBlock? ( BodyBasicNotTriples '.'? BodyTriplesBlock? )*` |
| `[26]` | `BodyBasicNotTriples` | ::= | `Filter` |
| `[27]` | `Assignment` | ::= | `'SET' '(' Var ':=' Expression ')'` |
| `[28]` | `DataTriplesBlock` | ::= | `TriplesSameSubjectData ( '.' DataTriplesBlock? )?` |
| `[29]` | `TriplesSameSubjectData` | ::= | `RDFTermData PropertyListNotEmptyData | TriplesNodeData PropertyListData | ReifiedTripleBlockData` |
| `[30]` | `PropertyListData` | ::= | `PropertyListNotEmptyData?` |
| `[31]` | `PropertyListNotEmptyData` | ::= | `VerbData ObjectListData ( ';' ( VerbData ObjectListData )? )*` |
| `[32]` | `VerbData` | ::= | `iri | 'a'` |
| `[33]` | `ObjectListData` | ::= | `ObjectData ( ',' ObjectData )*` |
| `[34]` | `ObjectData` | ::= | `GraphNodeData AnnotationData` |
| `[35]` | `GraphNodeData` | ::= | `RDFTermData | TriplesNodeData | ReifiedTripleData` |
| `[36]` | `TriplesNodeData` | ::= | `CollectionData | BlankNodePropertyListData` |
| `[37]` | `BlankNodePropertyListData` | ::= | `'[' PropertyListNotEmptyData ']'` |
| `[38]` | `CollectionData` | ::= | `'(' GraphNodeData+ ')'` |
| `[39]` | `AnnotationData` | ::= | `( ReifierData | AnnotationBlockData )*` |
| `[40]` | `AnnotationBlockData` | ::= | `'{|' PropertyListNotEmptyData '|}'` |
| `[41]` | `ReifierData` | ::= | `'~' ReifierIdData?` |
| `[42]` | `ReifierIdData` | ::= | `iri | BlankNode` |
| `[43]` | `ReifiedTripleBlockData` | ::= | `ReifiedTripleData PropertyListData` |
| `[44]` | `ReifiedTripleData` | ::= | `'<<' ReifiedTripleSubjectData VerbData ReifiedTripleObjectData ReifierData? '>>'` |
| `[45]` | `ReifiedTripleSubjectData` | ::= | `iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | ReifiedTripleData | TripleTermData` |
| `[46]` | `ReifiedTripleObjectData` | ::= | `iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | ReifiedTripleData | TripleTermData` |
| `[47]` | `TripleTermData` | ::= | `'<<(' TripleTermSubjectData VerbData TripleTermObjectData ')>>'` |
| `[48]` | `TripleTermSubjectData` | ::= | `iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | TripleTermData` |
| `[49]` | `TripleTermObjectData` | ::= | `iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | TripleTermData` |
| `[50]` | `HeadTemplateBlock` | ::= | `TriplesBlockTemplate` |
| `[51]` | `TriplesBlockTemplate` | ::= | `TriplesSameSubjectTemplate ( '.' TriplesBlockTemplate? )?` |
| `[52]` | `TriplesSameSubjectTemplate` | ::= | `VarOrRDFTerm PropertyListNotEmptyTemplate | TriplesNodeTemplate PropertyListTemplate | ReifiedTripleBlockTemplate` |
| `[53]` | `PropertyListTemplate` | ::= | `PropertyListNotEmptyTemplate?` |
| `[54]` | `PropertyListNotEmptyTemplate` | ::= | `Verb ObjectListTemplate ( ';' ( Verb ObjectListTemplate )? )*` |
| `[55]` | `ObjectListTemplate` | ::= | `ObjectTemplate ( ',' ObjectTemplate )*` |
| `[56]` | `ObjectTemplate` | ::= | `GraphNodeTemplate AnnotationTemplate` |
| `[57]` | `GraphNodeTemplate` | ::= | `VarOrRDFTerm | TriplesNodeTemplate | ReifiedTriple` |
| `[58]` | `TriplesNodeTemplate` | ::= | `CollectionTemplate | BlankNodePropertyListTemplate` |
| `[59]` | `BlankNodePropertyListTemplate` | ::= | `'[' PropertyListNotEmptyTemplate ']'` |
| `[60]` | `CollectionTemplate` | ::= | `'(' GraphNodeTemplate+ ')'` |
| `[61]` | `AnnotationTemplate` | ::= | `( Reifier | AnnotationBlockTemplate )*` |
| `[62]` | `AnnotationBlockTemplate` | ::= | `'{|' PropertyListNotEmptyTemplate '|}'` |
| `[63]` | `ReifiedTripleBlockTemplate` | ::= | `ReifiedTriple PropertyListTemplate` |
| `[64]` | `BodyTriplesBlock` | ::= | `TriplesBlockPattern` |
| `[65]` | `TriplesBlockPattern` | ::= | `TriplesSameSubjectPattern ( '.' TriplesBlockPattern? )?` |
| `[66]` | `ReifiedTripleBlockPattern` | ::= | `ReifiedTriple PropertyListPattern` |
| `[67]` | `TriplesSameSubjectPattern` | ::= | `VarOrRDFTerm PropertyListNotEmptyPattern | TriplesNodePattern PropertyListPattern | ReifiedTripleBlockPattern` |
| `[68]` | `PropertyListPattern` | ::= | `PropertyListNotEmptyPattern?` |
| `[69]` | `PropertyListNotEmptyPattern` | ::= | `( VerbPath | Var ) ObjectListPattern ( ';' ( ( VerbPath | Var ) ObjectListPattern )? )*` |
| `[70]` | `ObjectListPattern` | ::= | `ObjectPattern ( ',' ObjectPattern )*` |
| `[71]` | `ObjectPattern` | ::= | `GraphNodePattern AnnotationPattern` |
| `[72]` | `TriplesNodePattern` | ::= | `CollectionPattern | BlankNodePropertyListPattern` |
| `[73]` | `BlankNodePropertyListPattern` | ::= | `'[' PropertyListNotEmptyPattern ']'` |
| `[74]` | `CollectionPattern` | ::= | `'(' GraphNodePattern+ ')'` |
| `[75]` | `AnnotationPattern` | ::= | `( Reifier | AnnotationBlockPattern )*` |
| `[76]` | `AnnotationBlockPattern` | ::= | `'{|' PropertyListNotEmptyPattern '|}'` |
| `[77]` | `GraphNodePattern` | ::= | `VarOrRDFTerm | TriplesNodePattern | ReifiedTriple` |
| `[78]` | `Reifier` | ::= | `'~' ReifierId?` |
| `[79]` | `ReifierId` | ::= | `Var | iri | BlankNode` |
| `[80]` | `ReifiedTriple` | ::= | `'<<' ReifiedTripleSubject Verb ReifiedTripleObject Reifier? '>>'` |
| `[81]` | `ReifiedTripleSubject` | ::= | `Var | iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | ReifiedTriple | TripleTerm` |
| `[82]` | `ReifiedTripleObject` | ::= | `Var | iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | ReifiedTriple | TripleTerm` |
| `[83]` | `TripleTerm` | ::= | `'<<(' TripleTermSubject Verb TripleTermObject ')>>'` |
| `[84]` | `TripleTermSubject` | ::= | `Var | iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | TripleTerm` |
| `[85]` | `TripleTermObject` | ::= | `Var | iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | TripleTerm` |
| `[86]` | `Verb` | ::= | `VarOrIri | 'a'` |
| `[87]` | `VerbPath` | ::= | `Path` |
| `[88]` | `Path` | ::= | `PathSequence` |
| `[89]` | `PathSequence` | ::= | `PathEltOrInverse ( '/' PathEltOrInverse )*` |
| `[90]` | `PathEltOrInverse` | ::= | `PathElt | '^' PathElt` |
| `[91]` | `PathElt` | ::= | `( iri | 'a' | '(' Path ')' )` |
| `[92]` | `RDFTermData` | ::= | `iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | NIL | TripleTermData` |
| `[93]` | `VarOrRDFTerm` | ::= | `Var | iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | NIL | TripleTerm` |
| `[94]` | `VarOrIri` | ::= | `Var | iri` |
| `[95]` | `Var` | ::= | `VAR1 | VAR2` |
| `[96]` | `RDFLiteral` | ::= | `String ( LANG_DIR | '^^' iri )?` |
| `[97]` | `NumericLiteral` | ::= | `NumericLiteralUnsigned | NumericLiteralPositive | NumericLiteralNegative` |
| `[98]` | `NumericLiteralUnsigned` | ::= | `INTEGER | DECIMAL | DOUBLE` |
| `[99]` | `NumericLiteralPositive` | ::= | `INTEGER_POSITIVE | DECIMAL_POSITIVE | DOUBLE_POSITIVE` |
| `[100]` | `NumericLiteralNegative` | ::= | `INTEGER_NEGATIVE | DECIMAL_NEGATIVE | DOUBLE_NEGATIVE` |
| `[101]` | `BooleanLiteral` | ::= | `'true' | 'false'` |
| `[102]` | `String` | ::= | `STRING_LITERAL1 | STRING_LITERAL2 | STRING_LITERAL_LONG1 | STRING_LITERAL_LONG2` |
| `[103]` | `iri` | ::= | `IRIREF | PrefixedName` |
| `[104]` | `PrefixedName` | ::= | `PNAME_LN | PNAME_NS` |
| `[105]` | `BlankNode` | ::= | `BLANK_NODE_LABEL | ANON` |
| `[106]` | `Expression` | ::= | `ConditionalOrExpression` |
| `[107]` | `ConditionalOrExpression` | ::= | `ConditionalAndExpression ( '||' ConditionalAndExpression )*` |
| `[108]` | `ConditionalAndExpression` | ::= | `ValueLogical ( '&&' ValueLogical )*` |
| `[109]` | `ValueLogical` | ::= | `RelationalExpression` |
| `[110]` | `RelationalExpression` | ::= | `NumericExpression ( '=' NumericExpression | '!=' NumericExpression | '<' NumericExpression | '>' NumericExpression | '<=' NumericExpression | '>=' NumericExpression | 'IN' ExpressionList | 'NOT' 'IN' ExpressionList )?` |
| `[111]` | `NumericExpression` | ::= | `AdditiveExpression` |
| `[112]` | `AdditiveExpression` | ::= | `MultiplicativeExpression ( '+' MultiplicativeExpression | '-' MultiplicativeExpression | ( NumericLiteralPositive | NumericLiteralNegative ) ( ( '*' UnaryExpression ) | ( '/' UnaryExpression ) )* )*` |
| `[113]` | `MultiplicativeExpression` | ::= | `UnaryExpression ( '*' UnaryExpression | '/' UnaryExpression )*` |
| `[114]` | `UnaryExpression` | ::= | `'!' PrimaryExpression  | '+' PrimaryExpression  | '-' PrimaryExpression  | PrimaryExpression` |
| `[115]` | `PrimaryExpression` | ::= | `BrackettedExpression | BuiltInCall | iriOrFunction | RDFLiteral | NumericLiteral | BooleanLiteral | Var | ExprTripleTerm` |
| `[116]` | `iriOrFunction` | ::= | `iri ArgList?` |
| `[117]` | `ExprTripleTerm` | ::= | `'<<(' ExprTripleTermSubject Verb ExprTripleTermObject ')>>'` |
| `[118]` | `ExprTripleTermSubject` | ::= | `iri | RDFLiteral | NumericLiteral | BooleanLiteral | Var` |
| `[119]` | `ExprTripleTermObject` | ::= | `iri | RDFLiteral | NumericLiteral | BooleanLiteral | Var | ExprTripleTerm` |
| `[120]` | `BrackettedExpression` | ::= | `'(' Expression ')'` |
| `[121]` | `BuiltInCall` | ::= | `'STR' '(' Expression ')'  | 'LANG' '(' Expression ')'  | 'LANGMATCHES' '(' Expression ',' Expression ')'  | 'LANGDIR' '(' Expression ')'  | 'DATATYPE' '(' Expression ')'  | 'IRI' '(' Expression ')'  | 'URI' '(' Expression ')'  | 'BNODE' ( '(' Expression ')' | NIL )  | 'ABS' '(' Expression ')'  | 'CEIL' '(' Expression ')'  | 'FLOOR' '(' Expression ')'  | 'ROUND' '(' Expression ')'  | 'CONCAT' ExpressionList  | 'SUBSTR' '(' Expression ',' Expression ( ',' Expression )? ')'  | 'STRLEN' '(' Expression ')'  | 'REPLACE' '(' Expression ',' Expression ',' Expression ( ',' Expression )? ')'  | 'UCASE' '(' Expression ')'  | 'LCASE' '(' Expression ')'  | 'ENCODE_FOR_URI' '(' Expression ')'  | 'CONTAINS' '(' Expression ',' Expression ')'  | 'STRSTARTS' '(' Expression ',' Expression ')'  | 'STRENDS' '(' Expression ',' Expression ')'  | 'STRBEFORE' '(' Expression ',' Expression ')'  | 'STRAFTER' '(' Expression ',' Expression ')'  | 'YEAR' '(' Expression ')'  | 'MONTH' '(' Expression ')'  | 'DAY' '(' Expression ')'  | 'HOURS' '(' Expression ')'  | 'MINUTES' '(' Expression ')'  | 'SECONDS' '(' Expression ')'  | 'TIMEZONE' '(' Expression ')'  | 'TZ' '(' Expression ')'  | 'NOW' NIL  | 'UUID' NIL  | 'STRUUID' NIL  | 'IF' '(' Expression ',' Expression ',' Expression ')'  | 'STRLANG' '(' Expression ',' Expression ')'  | 'STRLANGDIR' '(' Expression ',' Expression ',' Expression ')'  | 'STRDT' '(' Expression ',' Expression ')'  | 'sameTerm' '(' Expression ',' Expression ')'  | 'isIRI' '(' Expression ')'  | 'isURI' '(' Expression ')'  | 'isBLANK' '(' Expression ')'  | 'isLITERAL' '(' Expression ')'  | 'isNUMERIC' '(' Expression ')'  | 'hasLANG' '(' Expression ')'  | 'hasLANGDIR' '(' Expression ')'  | 'REGEX' '(' Expression ',' Expression ( ',' Expression )? ')'  | 'isTRIPLE' '(' Expression ')'  | 'TRIPLE' '(' Expression ',' Expression ',' Expression ')'  | 'SUBJECT' '(' Expression ')'  | 'PREDICATE' '(' Expression ')'  | 'OBJECT' '(' Expression ')'` |

Productions for terminals:

|  |  |  |  |
| --- | --- | --- | --- |
| `[122]` | `IRIREF` | ::= | `` '<' ([^<>"{}|^`\]-[#x00-#x20] | UCHAR )* '>' `` |
| `[123]` | `PNAME_NS` | ::= | `PN_PREFIX? ':'` |
| `[124]` | `PNAME_LN` | ::= | `PNAME_NS PN_LOCAL` |
| `[125]` | `BLANK_NODE_LABEL` | ::= | `'_:' ( PN_CHARS_U | [0-9] ) ((PN_CHARS|'.')* PN_CHARS)?` |
| `[126]` | `VAR1` | ::= | `'?' VARNAME` |
| `[127]` | `VAR2` | ::= | `'$' VARNAME` |
| `[128]` | `LANG_DIR` | ::= | `'@' [a-zA-Z]+ ('-' [a-zA-Z0-9]+)* ('--' [a-zA-Z]+)?` |
| `[129]` | `INTEGER` | ::= | `[0-9]+` |
| `[130]` | `DECIMAL` | ::= | `[0-9]* '.' [0-9]+` |
| `[131]` | `DOUBLE` | ::= | `( ([0-9]+ ('.'[0-9]*)? ) | ( '.' ([0-9])+ ) ) [eE][+-]?[0-9]+` |
| `[132]` | `INTEGER_POSITIVE` | ::= | `'+' INTEGER` |
| `[133]` | `DECIMAL_POSITIVE` | ::= | `'+' DECIMAL` |
| `[134]` | `DOUBLE_POSITIVE` | ::= | `'+' DOUBLE` |
| `[135]` | `INTEGER_NEGATIVE` | ::= | `'-' INTEGER` |
| `[136]` | `DECIMAL_NEGATIVE` | ::= | `'-' DECIMAL` |
| `[137]` | `DOUBLE_NEGATIVE` | ::= | `'-' DOUBLE` |
| `[138]` | `STRING_LITERAL1` | ::= | `"'" ( ([^#x27#x5C#xA#xD]) | ECHAR | UCHAR )* "'"` |
| `[139]` | `STRING_LITERAL2` | ::= | `'"' ( ([^#x22#x5C#xA#xD]) | ECHAR | UCHAR )* '"'` |
| `[140]` | `STRING_LITERAL_LONG1` | ::= | `"'''" ( ( "'" | "''" )? ( [^'\] | ECHAR | UCHAR ) )* "'''"` |
| `[141]` | `STRING_LITERAL_LONG2` | ::= | `'"""' ( ( '"' | '""' )? ( [^"\] | ECHAR | UCHAR ) )* '"""'` |
| `[142]` | `ECHAR` | ::= | `'\' [tbnrf\"']` |
| `[143]` | `UCHAR` | ::= | `('\u' HEX HEX HEX HEX) | ('\U' HEX HEX HEX HEX HEX HEX HEX HEX)` |
| `[144]` | `NIL` | ::= | `'(' WS* ')'` |
| `[145]` | `WS` | ::= | `#x20 | #x9 | #xD | #xA` |
| `[146]` | `ANON` | ::= | `'[' WS* ']'` |
| `[147]` | `PN_CHARS_BASE` | ::= | `[A-Z] | [a-z] | [#x00C0-#x00D6] | [#x00D8-#x00F6] | [#x00F8-#x02FF] | [#x0370-#x037D] | [#x037F-#x1FFF] | [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] | [#x3001-#xD7FF] | [#xF900-#xFDCF] | [#xFDF0-#xFFFD] | [#x10000-#xEFFFF]` |
| `[148]` | `PN_CHARS_U` | ::= | `PN_CHARS_BASE | '_'` |
| `[149]` | `VARNAME` | ::= | `( PN_CHARS_U | [0-9] ) ( PN_CHARS_U | [0-9] | #x00B7 | [#x0300-#x036F] | [#x203F-#x2040] )*` |
| `[150]` | `PN_CHARS` | ::= | `PN_CHARS_U | '-' | [0-9] | #x00B7 | [#x0300-#x036F] | [#x203F-#x2040]` |
| `[151]` | `PN_PREFIX` | ::= | `PN_CHARS_BASE ((PN_CHARS|'.')* PN_CHARS)?` |
| `[152]` | `PN_LOCAL` | ::= | `(PN_CHARS_U | ':' | [0-9] | PLX ) ((PN_CHARS | '.' | ':' | PLX)* (PN_CHARS | ':' | PLX) )?` |
| `[153]` | `PLX` | ::= | `PERCENT | PN_LOCAL_ESC` |
| `[154]` | `PERCENT` | ::= | `'%' HEX HEX` |
| `[155]` | `HEX` | ::= | `[0-9] | [A-F] | [a-f]` |
| `[156]` | `PN_LOCAL_ESC` | ::= | `'\' ( '_' | '~' | '.' | '-' | '!' | '$' | '&' | "'" | '(' | ')' | '*' | '+' | ',' | ';' | '=' | '/' | '?' | '#' | '@' | '%' )` |

A text version of this grammar is available
[here](shapes-rule-language.bnf).

### 7.6 Selected Terminal Literal Strings

This document uses some specific terminal literal strings
EBNF-NOTATION. To clarify the Unicode code points used for these
terminal literal strings, the following table describes specific
characters used in this section.

| Code | Glyph | Description |
| --- | --- | --- |
| `U+000A` | `LF` | Line feed |
| `U+000D` | `CR` | Carriage return |
| `U+0023` | `#` | Number sign |
| `U+0025` | `%` | Percent sign |
| `U+005C` | `\` | Backslash |

## A. Example Imports Algorithm

The following algorithms show one way to resolve imports statements by
visiting all the referenced documents recursively.

The rule set merge of two rule sets, `RS1` and `RS2`,
is a rule set, `MR`, defined as follows:

```
define ruleSetMerge(rule set R1,rule Set RS2):
    MR.rules = RS1.rules ∪︀ RS2.rules
    MR.data = rdf_merge(RS1.data, RS2.data)
    MR.imports = {}
    the result is MR
enddefine

define imports(rule set RS, set of URLs V), returning rule set
    let I = the set of import URLs declared for the rule set RS
    let RS2 be a rule set formed from RS.rules and RS.data
    foreach URL x in I:
        if x ∉ V:
            V = V ∪︀ { x }
            read rule set RS3 from URL x
            RS2 = rulesetMerge(RS2, imports(RS3, V))
        endif
    endfor
    the result is RS2
enddefine

let RS be a rule set
let V = {}
if RS has a location, V = { location of RS }
result is imports(RS, V)
```

where `rdf\_merge` is the
RDF merge
operation.

## B. Internet Media Type and File Extension

The Internet Media Type (formerly known as MIME Type) for the
Shape Rules Language is
"`application/sparql-rl`".

The information that follows has been submitted to the Internet Engineering
Steering Group (IESG) for review, approval, and registration with IANA.

Type name:
:   application

Subtype name:
:   sparql-rl

Required parameters:
:   None

Optional parameters:

`version`
:   This parameter is optional.
    If present, acceptable values of `version` are defined in
    [Version Labels](#tab-version-labels).

`profile`
:   This parameter is optional and is used to include additional information.
    It does not change the semantics of the resource representation when
    processed without knowledge of the profile. The value of a
    `profile` parameter is a non-empty list of space-separated URIs.
    For more information and background, please refer to RFC6906.

Encoding considerations:
:   The syntax of the Shape Rules Language is expressed over code points in Unicode
    UNICODE. The encoding is always UTF-8 RFC3629.
:   Unicode code points may also be expressed using an \uXXXX (U+0 to U+FFFF) or
    \UXXXXXXXX syntax (for U+10000 onwards) where X is a hexadecimal digit [0-9A-F]

Security considerations:
:   See [C. Security Considerations](#security-considerations) as well as
    RFC3629 section 7, Security Considerations.

Interoperability considerations:
:   There are no known interoperability issues.

Published specification:
:   This specification.

Additional information:
:   Magic number(s):
    :   A SPARQL-RL file may have the string 'PREFIX'
        (case independent) near the beginning
        of the document.

    File extension(s):
    :   ".srl"

    Base URI:
    :   The SPARQL-RL 'BASE <IRIref>' term can change the
        current base URI for relative IRIrefs in the query language that
        are used sequentially later in the document.

Person & email address to contact for further information:
:   Data Shapes Working Group <public-shacl@w3.org;

Intended usage:
:   COMMON

Restrictions on usage:
:   None

Author/Change controller:
:   The SHACL 1.2 Rules specification is a work product of the World
    Wide Web Consortium's Data Shapes Working Group. The W3C has change
    control over these specifications.

## C. Security Considerations

TODO

SRL documents can contain `IMPORTS` statements that reference other SRL documents.
If an imported document itself contains its own `IMPORTS` statements,
those documents are also imported.

While useful to modularise rule sets, the use of `IMPORTS` statements can
introduce security risks.
Risks include, but are not limited to, rule sets
causing excessive computation, whether maliciously or accidental, while being evaluated;
and HTTP requests being intercepted and a different document being returned,
including out-of-date copies.

See [4.5 Processing Imports](#process-imports).

Need input on the security considerations.

## D. Privacy Considerations

TODO

## E. Internationalization Considerations

TODO

## F. Acknowledgements

TODO
