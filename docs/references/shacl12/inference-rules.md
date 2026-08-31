<!-- https://w3c.github.io/data-shapes/shacl12-inference-rules/ — W3C editors' draft, fetched 2026-08-31 -->

This document defines the Inference Rules support of the SHACL Shapes Constraint Language (SHACL).
While the Core part of SHACL focuses on the basic syntax of shapes and constraint validation of data graphs,
the SHACL Inference Rules cover features that can be used to infer new triples from existing triples in the data graph.

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

## 1. Introduction

This document specifies the Inference Rules support of the Shapes Constraint Language (SHACL).

### 1.1 Terminology

Throughout this document, the following terminology is used.

The SHACL inference rules defined in this document are sometimes simply called SHACL rules or even rules.
SHACL SPARQL rules are sometimes simply called SPARQL rules.

**Note:** Inference rules should not be confused with constraints.
Constraints define conditions that a data graph should conform to,
while rules define how additional (implicit) statements can be derived/inferred from the statements
that are explicitly asserted in a data graph.

Terminology that is linked to portions of RDF 1.2 Concepts and Abstract Syntax is used in SHACL Inference Rules as defined there.
Terminology that is linked to portions of other SHACL 1.2 documents is used in SHACL Inference Rules as defined there.
A single linkage is sufficient to provide a definition for all occurrences of a particular term in this document.

Definitions are complete within this document, i.e., if there is no rule to
make some situation true in this document then the situation is false.

This document uses the terms
RDF graph,
RDF triple,
IRI,
literal,
blank node,
node of an RDF graph,
datatype,
reifier,
RDF term, and
subject,
predicate, and
object of RDF triples
as defined in RDF 1.2 Concepts and Abstract Syntax rdf12-concepts.

This document uses the terms
focus node,
value,
value node,
constraint,
constraint component,
parameter,
mandatory parameter,
optional parameter,
parameter value,
shape,
node shape,
property shape,
SHACL property path,
SPARQL property path,
data graph,
shapes graph,
target,
validator,
node expression,
node expression function,
function name,
output nodes,
focus graph,
conform,
failure,
validation result,
SHACL instance,
SHACL subclass,
SHACL superclass,
SHACL type,
well-formed,
ill-formed,
as defined in the SHACL 1.2 Core specification shacl12-core.

This document uses the terms
binding,
pre-binding,
as defined in the SHACL 1.2 SPARQL specification shacl12-sparql.

### 1.2 Document Conventions

The syntax of SHACL is RDF.
The examples in this document use Turtle rdf12-turtle.
Other RDF serializations such as RDF/XML may be used in practice.
The reader should be familiar with basic RDF concepts rdf12-concepts such as triples and with SPARQL sparql12-query.

Within this document, the following namespace prefix bindings are used:

| Prefix | Namespace |
| --- | --- |
| `owl:` | `http://www.w3.org/2002/07/owl#` |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` |
| `sh:` | `http://www.w3.org/ns/shacl#` |
| `shnex:` | `http://www.w3.org/ns/shacl-node-expr#` |
| `sparql:` | `http://www.w3.org/ns/sparql#` |
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
the namespace above, i.e. it includes the `#`.
References to the SHACL vocabulary, e.g. via `owl:imports` should include the `#`.

Throughout the document, color-coded boxes containing RDF graphs in Turtle will appear.
These fragments of Turtle documents use the prefix bindings given above.

```
# This box represents an input shapes graph

<s> ex:p <o> .
					
```

```
# This box represents an input data graph.
					
```

```
# This box represents the inferred triples that are produced by the rules
					
```

Grey boxes such as this include syntax rules that apply to the shapes graph.

SPARQL variables using the `$` marker represent external bindings that are pre-bound in the SPARQL query before execution.

`true` denotes the RDF term `"true"^^xsd:boolean`.
`false` denotes the RDF term `"false"^^xsd:boolean`.

### 1.3 Conformance

This document defines the **SHACL Inference Rules** framework that extends SHACL Core.
This specification describes conformance criteria for:

- **SHACL inference rule processors** as processors that support the evaluation of rules

Also see the discussion of well-formedness in the Conformance section of SHACL Core.

## 2. Getting Started with SHACL Inference Rules

SHACL defines an RDF vocabulary to describe shapes - collections of constraints that apply to a set of nodes.
Shapes can be associated with nodes using a flexible target mechanism, e.g. for all instances of a class.
One focus area of SHACL is data validation.
However, the same principles of describing data patterns in shapes can also be exploited for other purposes.
SHACL rules build on SHACL to form a light-weight RDF vocabulary for the exchange of rules that can be used
to derive inferred RDF triples from existing *asserted* triples.

The SHACL rules feature defined in this document includes a general framework using the properties
such as `sh:rule` and `sh:condition`, plus an extension mechanism for specific rule types.
This document defines two such rule types: SHACL SPARQL rules and triple rules.

### 2.1 An Example SPARQL Rule

The following example illustrates a simple use case of a SPARQL rule that applies to all instances of
the class `ex:Rectangle` and computes the values of the `ex:area` property by multiplying
the rectangle's width and height:

**Example: A SPARQL rule to compute the area of a Rectangle**

```
ex:RectangleShape
	a sh:NodeShape ;
	sh:targetClass ex:Rectangle ;
	sh:property [
		sh:path ex:color ;
		sh:datatype xsd:string ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
	] ;
	sh:property [
		sh:path ex:width ;
		sh:datatype xsd:integer ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
	] ;
	sh:property [
		sh:path ex:height ;
		sh:datatype xsd:integer ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
	] .

ex:RectangleRulesShape
	a sh:NodeShape ;
	sh:targetClass ex:Rectangle ;
	sh:rule [
		a sh:SPARQLRule ;
		sh:construct """
			CONSTRUCT {
				$this ex:area ?area .
			}
			WHERE {
				$this ex:width ?width .
				$this ex:height ?height .
				BIND (?width * ?height AS ?area) .
			}
			""" ;
		# Rule only applies to Rectangles that conform to ex:RectangleShape
		sh:condition ex:RectangleShape ;
	] .
						
```

An engine that is capable of executing such rules uses the target statements associated
with the shapes in the shapes graph to determine which rules need to be executed on which target nodes.
For those target nodes that conform to any [condition shapes](#condition), it executes the provided
CONSTRUCT queries to produce the inferred triples.
During the execution of the query, the variable `this` has the current focus node as pre-bound variable.

For the following data graph, the triples below would be produced.

**Example: Sample instance data for the rectangle rule**

```
ex:ExampleRectangle
	a ex:Rectangle ;
	ex:color "green" ;
	ex:width 7 ;
	ex:height 8 .

ex:InvalidRectangle    # Lacks a value for ex:color, so sh:condition is not met
	a ex:Rectangle ;
	ex:width 2 ;
	ex:height 6 .
						
```

```
ex:ExampleRectangle ex:area 56 .
						
```

### 2.2 An Example Triple Rule

In addition to SPARQL-based inference rules, this document introduces triple rules.
These rules rely on node expressions instead of SPARQL queries to compute the inferred triples.
Here is the same scenario as the previous example, using a triple rule.

**Example: A triple rule to compute the area of a Rectangle**

```
ex:RectangleShape
	a sh:NodeShape ;
	sh:targetClass ex:Rectangle ;
	sh:property [
		sh:path ex:color ;
		sh:datatype xsd:string ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
	] ;
	sh:property [
		sh:path ex:width ;
		sh:datatype xsd:integer ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
	] ;
	sh:property [
		sh:path ex:height ;
		sh:datatype xsd:integer ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
	] .

ex:RectangleRulesShape
	a sh:NodeShape ;
	sh:targetClass ex:Rectangle ;
	sh:rule [
		a sh:TripleRule ;
		# Rule only applies to Rectangles that conform to ex:RectangleShape
		sh:condition ex:RectangleShape ;
		sh:predicate ex:area ;  # This predicate will be inferred
		sh:object [  # The object(s) will be computed with this node expression
			sparql:multiply (
				[ shnex:pathValues ex:width ]
				[ shnex:pathValues ex:height ]
			)
		] ;
	] .
						
```

## 3. Syntax of SHACL Rules

The SHACL instances of `sh:Rule`, including its subclasses `sh:SPARQLRule` and `sh:TripleRule`,
are called SHACL rules.
SHACL has a flexible, extensible design in which multiple types of rules can be supported,
but this document only defines two of them: SPARQL rules and triple rules.

Each rule type is identified by an IRI that is used as
their `rdf:type`.
Each rule type also defines execution instructions that can be implemented by rule engines.

Each SHACL rule has at least one `rdf:type`
which is a IRI.

Rules can have multiple types, e.g., to provide instructions that work either in SPARQL or JavaScript,
depending on the capabilities of the engine.
The creator of such rules needs to make sure that such rules have consistent semantics.
Rule `R` has rule type `T` if `R` is a SHACL instance of `T`.

### 3.1 Shape Rules and Global Rules (sh:rule)

The property `sh:rule` can be used to link a shape (subject)
with a shape rule (object).
The subjects of `sh:rule` triples are IRIs.

SHACL rules can be divided into two categories:

- A shape rule is a rule that is the object of a `sh:rule` triple.
  Shape rules are executed for all target nodes of the shape which is the subject
  of the `sh:rule` triple.
- A global rule is a rule that is *not* linked to a shape by
  a `sh:rule` predicate.

An example of a shape rule was shown above in .

The following example illustrates a global rule.

**Example: A global rule (not associated with any shape)**

```
ex:SymmetricPropertyRule
	a sh:SPARQLRule ;
	sh:construct """
		CONSTRUCT {
			?o ?p ?s .
		}
		WHERE {
			?p a ex:SymmetricProperty .
			?s ?p ?o .
		}
		""" .
						
```

### 3.2 Conditions on Shape Rules (sh:condition)

A shape rule may have values for the property `sh:condition` to specify shapes
that the target nodes must conform to before they become focus nodes for the rule.

The values of `sh:condition` at a rule must be well-formed shapes.

If the value `C` of `sh:condition` is a SHACL instance of both `sh:NodeShape`
and `rdfs:Class`, then the focus nodes must also conform to the constraints of the
non-deactivated SHACL superclasses of `C`
that are also SHACL instances of both `sh:NodeShape` and `rdfs:Class`.
This is similar to how Implicit Class Targets are interpreted during validation.

### 3.3 Deactivated Rules (sh:deactivated)

Rules may be *deactivated* by setting `sh:deactivated` to `true`.
Deactivated rules are ignored by the rules engine.

Each rule may have at most one value for the
property `sh:deactivated`.
The values of `sh:deactivated` are either
of the `xsd:boolean` literals `true` or `false`.

### 3.4 Grouping of Rules into Layers (sh:layer)

Rules may be grouped into layers, identified by a numeric value.
During execution, a SHACL rules engine will iterate over all rules in the same layer
before moving to the next layer.
Layers with a smaller numeric value will be executed before those with a larger number.

Each rule may have at most one value for the
property `sh:layer`.
The values of `sh:layer` at rules
are literals with datatype `xsd:integer`.

If unspecified, then the default layer of a rule is `0`.

An example of `sh:layer` to control the execution order of rules is provided in .

### 3.5 Ordering of Rules (sh:order)

Rules may specify their relative execution order within the same layer as defined in this section.

Each rule may have at most one value for the
property `sh:order`.
The values of `sh:order` at rules
are literals with datatype `xsd:decimal` or `xsd:integer`.

If unspecified, then the default execution order is `0`.
When the rules are executed, within the same layer, rules with larger order values will be executed after those with smaller values.

**Example: Rule order example**

```
ex:RuleOrderExampleShape
	a sh:NodeShape ;
	sh:targetClass ex:Person ;
	sh:rule [
		a sh:SPARQLRule ;
		rdfs:label "Infer uncles, i.e. male siblings of the parents of $this" ;
		sh:order 1 ;   # Will be evaluated before 2
		sh:construct """
			CONSTRUCT {
				$this ex:uncle ?uncle .
			}
			WHERE {
				$this ex:parent ?parent .
				?parent ex:sibling ?uncle .
				?uncle ex:gender ex:male .
			}
			"""
	] ;
	sh:rule [
		a sh:SPARQLRule ;
		rdfs:label "Infer cousins, i.e. the children of the uncles" ;
		sh:order 2 ;
		sh:construct """
			CONSTRUCT {
				$this ex:cousin ?cousin .
			}
			WHERE {
				$this ex:uncle ?uncle .
				?cousin ex:parent ?uncle .
			}
			"""
	] .
						
```

### 3.6 Run-once Rules (sh:runOnce)

A SHACL rules engine iterates over the rules, allowing the same rule to be
executed multiple times until no further triples are inferred.
However, some rules may produce fresh blank nodes with each execution and therefore cause infinite iterations.

Rules may use the property `sh:runOnce` to instruct a rules engine that the rule is
only executed once and before the other rules in the same layer.

Each rule may have at most one value for the
property `sh:runOnce`.
The values of `sh:runOnce` at rules
are literals with datatype `xsd:boolean`.

A run-once rule is a rule for which at most one iteration is performed (per shape, if it is a shape rule), i.e. it is executed at most once per focus node.
All other rules are called iterating rules.
A rule that has `true` as its value for `sh:runOnce` is a run-once rule.

**Example: Example of run-once rules and layers**

```
ex:RunBeforeRule
	a sh:SPARQLRule ;
	sh:runOnce true ;
	sh:layer 0 ;     # This triple is optional (0 is the default layer)
	sh:construct """
		CONSTRUCT {
			ex:Grandma a ex:Person .
			ex:Son a ex:Person .
			ex:Grandson a ex:Person .
			ex:Granddaughter a ex:Person .
			ex:Grandma ex:child ex:Son .
			ex:Son ex:child ex:Grandson .
			ex:Son ex:child ex:Granddaughter .
		}
		WHERE {
		}
		""" .

ex:Person
	a sh:ShapeClass ;
	sh:rule ex:IteratingRule ;
	sh:rule ex:RunAfterRule .

ex:IteratingRule
	a sh:SPARQLRule ;
	rdfs:comment "This is a recursive rule that needs to iterate multiple times." ;
	sh:layer 0 ;     # This triple is optional (0 is the default layer)
	sh:construct """
		CONSTRUCT {
			$this ex:offspring ?offspring .
		}
		WHERE {
			$this ex:child/ex:offspring? ?offspring .
		}
		""" .

ex:RunAfterRule
	a sh:SPARQLRule ;
	sh:runOnce true ;
	sh:layer 1 ;    # Execute after the iterating rules have finished
	sh:construct """
		CONSTRUCT {
			?reifier rdf:reifies ?triple .
			?reifier ex:source sh:Rules .
		}
		WHERE {
			$this ex:offspring ?offspring .
			BIND (BNODE() AS ?reifier) .
			BIND (TRIPLE($this, ex:offspring, ?offspring) AS ?triple) .
		}
		""" .
						
```

```
ex:Grandma
	a ex:Person ;
	ex:child ex:Son ;
	ex:offspring ex:Son {| ex:source sh:Rules |} ;
	ex:offspring ex:Grandson {| ex:source sh:Rules |} ;
	ex:offspring ex:Granddaughter {| ex:source sh:Rules |} .

ex:Son
	a ex:Person ;
	ex:child ex:Grandson, ex:Granddaughter ;
	ex:offspring ex:Grandson {| ex:source sh:Rules |} ;
	ex:offspring ex:Granddaughter {| ex:source sh:Rules |} .

ex:Grandson
	a ex:Person .

ex:Granddaughter
	a ex:Person .
						
```

### 3.7 Expected Derived Triples (sh:expectedPredicate)

SHACL Core includes the following properties to *derive* property values that are not necessarily asserted in the data graph:

- `sh:defaultValue` defines what values should be used
  when no other values are present for a property.
  For example, the default value of `ex:childCount` could be `0`.
- `sh:values` defines general instructions for computing
  derived values for a property.
  For example, the `ex:area` of a rectangle may be derived by multiplying its `ex:width` and `ex:height`.

Both properties can use node expressions including those defined in .
Both properties can only be used to compute the objects of a given predicate for the
subjects that are targeted by shapes.
This means that `sh:defaultValue` and `sh:values` describe implicit triples
that are similar to inferences produced by rules.

When a rule refers to a certain property, it is reasonable for the rule to expect that these
implicit triples are present.
This section explains how rules can make sure that such derived triples are present before the rule executes.

For a given predicate `p`, the derived value nodes are all value nodes
that can be computed using `sh:defaultValue` and `sh:values`
as defined by  in any (non-deactivated)
property shape that uses `p` as `sh:path` in the shapes graph.
For these derived value nodes `v` the derived triples are the triples
where `v` is the object, `p` is the predicate and the subjects
are the target nodes of the property shapes.

The expected derived triples of a rule are the derived triples for all values
of the property `sh:expectedPredicate` at the rule.
All this is best explained by an example:

**Example: Example of expected derived triples**

```
ex:RectangleShape
	a sh:NodeShape ;
	sh:targetClass ex:Rectangle ;
	sh:property ex:RectangleShape-area ;
	sh:rule ex:Rectangle-computeSmall .

ex:RectangleShape-area
	a sh:PropertyShape ;
	sh:path ex:area ;
	sh:defaultValue 1 ;
	sh:values [
		sparql:multiply ( [ shnex:pathValues ex:width ] [ shnex:pathValues ex:height ] )
	] .

ex:Rectangle-computeSmall
	a sh:SPARQLRule ;
	rdfs:comment "This rule expects that the values of ex:area have been derived." ;
	sh:expectedPredicate ex:area ;
	sh:construct """
		CONSTRUCT {
			$this ex:isSmall true .
		}
		WHERE {
			$this ex:area ?area .
			FILTER (?area < 100) .
		}
	""" .
						
```

The following data graph defines some rectangle instances:

```
ex:IncompleteRectangle
	a ex:Rectangle .

ex:SmallRectangle
	a ex:Rectangle ;
	ex:width 4 ;
	ex:height 5 .

ex:LargeRectangle
	a ex:Rectangle ;
	ex:width 11 ;
	ex:height 10 .
						
```

```
# Derived triples, visible only while rules execute:
# ex:IncompleteRectangle ex:area 1 .
# ex:SmallRectangle ex:area 20 .
# ex:LargeRectangle ex:area 110 .

# Inferred triples:
ex:IncompleteRectangle ex:isSmall true .
ex:SmallRectangle ex:isSmall true .
						
```

A SHACL rules engine will remove the derived triples from the inferences at the end of
processing each layer, except those triples that have also been inferred by rules.
Some engines may have a setting to keep all derived triples, for example
when data is exported to systems that do not support SHACL.

## 4. Rule Sets

The input to a SHACL rules processor is a set of rules called a rule set.
A rule set is identified by an IRI.
The property `sh:hasRule` can be used to declare that a rule set has a given rule as a member.
The default rule set of a graph is the set of all rules in the graph.
Rule sets can use the property `sh:includesRuleSet` to (transitively) include other rule sets.

All SHACL instances of `sh:RuleSet` have a IRI.
Rule sets can have values for `sh:hasRule` and those values are rules.
The values of `sh:includesRuleSet` at a rule set are IRIs.

**Example: Example of rules and rule sets**

```
ex:Rule1
	a sh:SPARQLRule ;
	sh:construct "..." .

ex:Rule2
	a sh:SPARQLRule ;
	sh:construct "..." .

ex:RuleSet1
	a sh:RuleSet ;
	sh:includesRuleSet ex:RuleSet2 ;
	sh:hasRule ex:Rule1 .

ex:RuleSet2
	a sh:RuleSet ;
	sh:hasRule ex:Rule2 .
					
```

The rule set `ex:RuleSet1` contains `ex:Rule1` and `ex:Rule2`
(via `ex:RuleSet2`), while `ex:RuleSet2` contains only `ex:Rule2`.

## 5. Rules Graph

A rules graph is a shapes graph that contains SHACL rules.

The `sh:RulesGraph` class MAY be used as an `rdf:type`
of the IRI of a graph that typically acts in the role of a rules graph.

*The remainder of this section is non-normative.*

The graph type classes (`sh:DataGraph`, `sh:ShapesGraph`, `sh:RulesGraph`)
represent roles that are not mutually exclusive; a single graph MAY be typed with more than one of these classes.
Rules graphs MAY contain `sh:rule` triples that reference shapes defined in
other graphs, allowing rules to be managed independently of shape and ontology definitions.

## 6. The sh:Rules Entailment Regime

SHACL defines the property `sh:entailment`
to link a shapes graph with *entailment regimes*.
The IRI `sh:Rules` represents the SHACL rules entailment regime.
In the following example, the shapes graph indicates to a SHACL validation engine that the SHACL rules
inside of the shapes graph need to be executed prior to starting the validation.

**Example: Activating SHACL Inference Rules entailment**

```
<http://example.org/my-shapes>
	a owl:Ontology ;
	sh:entailment sh:Rules .
					
```

Following the general policy for SHACL, validation engines that do *not* support the SHACL rules entailment regime
MUST signal a failure if this triple is present.
Validation engines that do support the SHACL rules entailment regime execute the rules following the
[rules execution instructions](#rules-execution) prior to performing the actual validation.

## 7. Temporary Triples

It is sometimes useful for inference rules to produce triples that are only visible during the execution
of other rules but do not end up in the final inferences.
A temporary triple is an inferred triple for which the inference graph contains a
reifier with the value `sh:tempTriple true`.
Temporary triples and their reifiers are visible to executing rules.
Rules can produce such triples as illustrated in the following example:

**Example: An example rule that produces temporary triples**

```
ex:Person
	a sh:ShapeClass ;
	sh:rule ex:CollectOffspringsRule ;
	sh:rule ex:SetYoungestOffspringsRule .

ex:CollectOffspringsRule
	a sh:SPARQLRule ;
	sh:layer 0 ;
	sh:runOnce true ;
	sh:construct """
		CONSTRUCT {
			$this ex:offspring ?offspring {| sh:tempTriple true |} .
		}
		WHERE {
			$this ex:child+ ?offspring .
		}
	""" .

ex:SetYoungestOffspringsRule
	a sh:SPARQLRule ;
	sh:layer 1 ;
	sh:construct """
		CONSTRUCT {
			$this ex:youngestOffspring ?o .
		}
		WHERE {
			{
				SELECT $this ?o
				WHERE {
					$this ex:offspring ?o .
					?o ex:age ?age .
				}
				ORDER BY ?age
				LIMIT 1
			}
		}
	""" .
					
```

The first rule computes `ex:offspring` triples as the (transitive)
children of each Person.
The second rule uses the `ex:offspring` triples to infer the `ex:youngestOffspring`
of each Person.
The final inferences only include the `ex:youngestOffspring` triples.
All temporary triples, i.e., triples whose reifier is marked with `sh:tempTriple true`,
are automatically deleted by the SHACL engine at the end of the inference process.

Creating temporary triples can be helpful when a computation is too complex to be carried out by a single rule.
The complex computation can then be decomposed into *multiple* rules:
some rules infer *partial* results, from which other rules derive the *final* results.
The partial results are only functional to the computation of the final results and are no longer needed once the latter have been obtained.
By marking these partial results as temporary triples, they are automatically removed after the final results have been computed.

## 8. General Execution Instructions for SHACL Rules

A SHACL rules engine is a computer procedure that takes as input
a data graph, a shapes graph and an optional rule set (defaulting to the default rule set of the shapes graph)
and is capable of adding triples to the data graph.
The new triples that are produced by a rules engine are called the inferred triples.

Note that, from a logical perspective, the data graph will be *modified* if triples get inferred.
This means that rules can trigger after other triples have been inferred.
However, in cases where the original data should not be modified, implementations may construct a logical data graph
that has the original data as one subgraph and a dedicated inferences graph as another subgraph, and where
the inferred triples get added to the inferences graph only.

An execution of a rule is the process that produces inferred triples from the rule
based on the execution instructions of its rule types.
If the rule is a shape rule (i.e., it is linked to at least one shape via `sh:rule`),
then the rule is executed for each target node of each of the linked and non-deactivated
shapes that conform to all non-deactivated [conditions](#condition) of the rule.
These target nodes become the focus nodes of the executing shape rule.

For a given rule set in the shapes graph
an iteration is a single execution of each individual rule in the order as
specified by [3.5 Ordering of Rules (sh:order)](#rule-order), skipping the rules that are [deactivated](#deactivated-rules).
Within an iteration, the inferred triples of one rule become immediately visible to the next rule.

The execution of a rule set is defined as follows:

```
					For all layers in the rule set (in ascending order):
						Compute the expected derived triples for all rules in the layer
						Execute one iteration over all run-once rules in the layer
						do
							Execute one iteration over all iterating rules in the layer
						while the iteration has produced newly inferred triples
						Delete the derived triples (except those that were also inferred by rules)
							and their reifiers

					Delete the temporary triples and their reifiers
				
```

If any of the rules reports a failure during execution,
then the execution of a rule set also produces a failure.

If a rules engine is not able to execute a given rule
because it does not support any of the rule types of the rule,
then it reports a failure.

Rule engines MAY also report a failure after a pre-configured maximum iteration count has been exceeded or
a pre-configured maximum number of inferred triples has been produced.
This can help as a guard to avoid out-of-memory problems and infinite loops.

At no time are inferred triples visible to the shapes graph, i.e. it is impossible for rules
to modify the definitions of rules or shapes.

## 9. Tracking the Rule that has produced a Triple (sh:sourceRule)

Rule engines MAY have an option to generate additional triples that can be used to track
which rules have produced the inferred triples.
The property `sh:sourceRule` can be used in a reifier of a triple in the inferences graph
to link the triple with the rule.
The values of `sh:sourceRule` SHOULD be IRIs.

The following example indicates that the triple `ex:Alice ex:friend ex:Bob` has been
inferred by the rule `ex:SymmetricPropertyRule`.

```
<< ex:Alice ex:friend ex:Bob >> sh:sourceRule ex:SymmetricPropertyRule .
```

Fully expanded into RDF triples this is equivalent to:

```
_:id rdf:reifies <<( ex:Alice ex:friend ex:Bob )>> .
_:id sh:sourceRule ex:SymmetricPropertyRule .
```

If a rule engine adds these triples, the triples MUST NOT be visible to executing rules.

## 10. Variations of SHACL Rule Implementations

The [general execution algorithm](#rules-execution) described above is intentionally
kept generic and offers a lot of flexibility to specific implementations.
In particular, the algorithm is non-deterministic in the sense that unless the order of rules
is specified explicitly, the results may differ across executions.
This is, for example, the case when rules draw conclusions from the number of certain triples
yet those triples may be produced by other rules.
In this document, the responsibility of producing a predictable ordering and layering/grouping of
rules is left to the rule author.

Some SHACL rule implementations MAY implement different algorithms to determine
the run-once rules (ignoring `sh:runOnce`),
the [rule order](#rule-order) (ignoring `sh:order`), and
the [layers](#rule-layers) (ignoring `sh:layer`).
This can, for example, be used by engines that support controlled subsets of SHACL rules
for which it is possible to compute rule dependencies automatically.
Another example is a rule engine that automatically prevents infinite loops because rules
generate blank nodes.
These implementation MAY produce different results from those that only rely on the
explicitly given `sh:order`, `sh:runOnce` and `sh:layer` values.

Some SHACL rule implementations MAY also report additional failures that are not reported
by the default algorithm.

This would be a good place to cross-reference the ongoing SRL work, if this becomes a SHACL Rules variation.

## 11. Built-in Rule Types

The SHACL inference rules framework defines a general syntax of rules and their execution algorithm.
This document defines the two rule types from the following two subsections.

Note that not all implementations are required to implement both of these types for conformance.
A rules engine that encounters a rule for which it does not implement any
rule type reports a failure, as defined in [8. General Execution Instructions for SHACL Rules](#rules-execution).

### 11.1 SHACL SPARQL Rules

This section defines a rule type called SHACL SPARQL rules, often just "SPARQL Rules",
identified by the IRI `sh:SPARQLRule`.
SPARQL rules have the following properties:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:construct` | The SPARQL CONSTRUCT query. SPARQL rules must have exactly one value for the property `sh:construct`. The values of `sh:construct` are literals with datatype `xsd:string`. |
| `sh:prefixes` | The prefixes to use to turn the `sh:construct` into a SPARQL query. SPARQL rules may use the property `sh:prefixes` to declare a dependency on prefixes based on the mechanism defined in Prefix Declarations for SPARQL Queries. This mechanism allows users to abbreviate URIs in the `sh:construct` strings. |

Let `Q` be the SPARQL CONSTRUCT query derived from the values of the properties
`sh:construct` and `sh:prefixes` of the SPARQL rule in the shapes graph.

- If the rule is a shape rule:
  For each focus node, execute the query `Q`
  pre-binding the variable `this` to the focus node,
  and infer the constructed triples.
- If the rule is a global rule:
  Execute the query `Q` without any pre-binding,
  and infer the constructed triples.

**Note:** For SPARQL rules that are shape rules (i.e., linked to a shape with `sh:rule`),
a SHACL rule engine also counts as a SHACL-SPARQL processor
and the syntax limitations required by pre-binding do apply to shape rules.
Since global SPARQL rules do not use pre-binding, the syntax limitations
required by pre-binding do not apply to them.

### 11.2 Triple Rules

This section defines a rule type called triple rules, identified by
the IRI `sh:TripleRule`.
Triple rules have the following properties:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:subject` | The node expression used to compute the subjects of the triples. Each triple rule must have at most one value of the property `sh:subject` (which must be a well-formed node expression). |
| `sh:predicate` | The node expression used to compute the predicates of the triples. Each triple rule must have at most one value of the property `sh:predicate` (which must be a well-formed node expression). |
| `sh:object` | The node expression used to compute the objects of the triples. Each triple rule must have at most one value of the property `sh:object` (which must be a well-formed node expression). |

Let `S`, `P` and `O` be the sets of nodes produced by evaluating
the node expressions that are the values of `sh:subject`, `sh:predicate`
and `sh:object` respectively at the triple rule.
Where `sh:subject`, `sh:predicate`, or `sh:object` are absent, use
the list consisting of the current focus node (which is empty for global rules).
For each combination of members `s` of `S`, `p` of `P` and
`o` of `O`, infer a triple with subject `s`,
predicate `p` and object `o`.
Skip ill-formed triples, for example when a blank node is used as predicate.

**Example: An example triple rule computing instances of Square**

In this example, any instance of `ex:Rectangle` where the width equals the height
will receive an extra `rdf:type ex:Square` triple.

```
ex:Rectangle
	a sh:ShapeClass ;
	rdfs:label "Rectangle" ;
	sh:property [
		sh:path ex:height ;
		sh:datatype xsd:integer ;
		sh:maxCount 1 ;
		sh:minCount 1 ;
		sh:name "height" ;
	] ;
	sh:property [
		sh:path ex:width ;
		sh:datatype xsd:integer ;
		sh:maxCount 1 ;
		sh:minCount 1 ;
		sh:name "width" ;
	] ;
	sh:rule [
		a sh:TripleRule ;
		# sh:subject defaults to the current focus node
		sh:predicate rdf:type ;
		sh:object ex:Square ;
		sh:condition ex:Rectangle ;
		sh:condition [
			sh:property [
				sh:path ex:width ;
				sh:equals ex:height ;
			] ;
		] ;
	] .							
						
```

```
ex:InvalidRectangle
	a ex:Rectangle .

ex:NonSquareRectangle
	a ex:Rectangle ;
	ex:height 2 ;
	ex:width 3 .

ex:SquareRectangle
	a ex:Rectangle ;
	ex:height 4 ;
	ex:width 4 .
						
```

```
	ex:SquareRectangle rdf:type ex:Square .
						
```

**Example: An example triple rule computing the number of children of a Person**

In this example, a SHACL rules engine will infer a `ex:childCount` triple for any instance of `ex:Person`
using a node expression combining `shnex:count` and `shnex:pathValues`.

```
ex:PersonShape
	a sh:NodeShape ;
	sh:targetClass ex:Person ;
	sh:rule ex:PersonShape-childCount-rule .

ex:PersonShape-childCount-rule
	a sh:TripleRule ;
	sh:runOnce true ;
	sh:predicate ex:childCount ;
	sh:object [
		shnex:count [
			shnex:pathValues ex:child
		]
	] .
						
```

```
ex:Dad
	a ex:Person ;
	ex:child ex:SomeDaughter ;
	ex:child ex:SomeSon .
						
```

```
	ex:Dad ex:childCount 2 .
						
```

## A. Summary of Syntax Rules

This section enumerates all normative syntax rules of this document.
This section is automatically generated from other parts of this spec and hyperlinks are provided back
into the prose if the context of the rule in unclear.
Nodes that violate these rules in a shapes graph are ill-formed.

| Syntax Rule Id | Syntax Rule Text |
| --- | --- |

## B. Security and Privacy Considerations

Applying a SHACL inference rule set to a data graph can result in
significant computation and memory usage, which may be exploited
to cause denial of service.
Applications should take care to limit the amount of computation and
memory usage that can be caused by applying such rule sets.

SHACL inference rules can be used to process and create arbitrary application data;
security considerations will vary by domain of use.
Security/privacy protocols should be imposed which reflect the sensitivity of the information in the outcome of rule set evaluation.

Security considerations of this document include all the security considerations of
SHACL SPARQL,
SHACL Core.

## C. Acknowledgements

Original SHACL core specifications were produced by the RDF Data Shapes Working Group.
See the [Core specification's Acknowledgements section](https://www.w3.org/TR/2017/REC-shacl-20170720/#ack) and
the [Advanced Features specification's Acknowledgements section](https://www.w3.org/TR/2017/NOTE-shacl-af-20170608/#ack).
