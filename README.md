# Experimental Tools for Sesquicentennial Workflows

The repository here includes experimental tools for generating hand written text and metadata about handwritten
documents for Sesquicentennial related works.

This is a work in progress but the idea is to write prompts as markdown (you can see those in `prompts`) and use Claude for HTR
and metadata generation.

## Sample Output using claude-3-5-haiku-20241022

```
```
```
Extracted text:
Columbus Texas
June 16th 1858

Dear M[illegible],

Though I feel very little like writing you I much use you the condition I am in and the feelings I experience this eve can be nothing more than a note. The news consisted in Houston, and I at wood softly at home yesterday, at 2:10 9 P.M. As I anticipated I found my father in the coldest state of rest treatment, and the deepest chose of sorrow agony. Time with the greatest effort of my life that I controlled my overflowing grief sufficiently to become a comforter to him. At time, I may comfort him to some extent; myself to none. Grief is my portion of grief. I must bear. My little boy's body is still in the river or - but [illegible]

not equal of the terrible thought! They have quietly complete the dear childly though now explain, in every place & manner, at first like a man adept, yet I know I am not faultless. In this I will send the rumination mostly of my Elysian please hand them in submitting the necessary remark. Chancet it so happen that you leave before my return don't forget to give the key to the [illegible]. I would return the last of this went but cannot if matters remain as they now are.

I know that you appreciate my feelings enough to think nothing may of this futile attempt at accompanying a letter. Give my regards to the Prof. especially our friend Re[illegible] a medium through which I may send best wishes to my other young ladies. Enough for the present.

Trustday the 18[illegible] on the day of punishing the stone were facilities lady, was found in the river, some fifteen miles below. Some in a frightful condition, but me managed to get him home and properly noticed. The buried occurred yesterday morning at 10 o'clock. No notices of a funeral were detailed but many friends were sent to witness the burial of my boy- then stopped, now I hope safely. Sister seems better reconciled since the recovery & burial of his little boy.

I shall be the last of next week before I can return to the College then to remain not busy. If you know of anything you want of me let me know by letter, or it will come to your mind. For late you have me a note on our table. Ringley

==================================================

Here's my metadata analysis of the historical letter:

```
```
json
{
  "dublin_core": {
    "title": {
      "value": "Personal Letter Describing Family Tragedy in Columbus, Texas",
      "confidence": "high",
      "reasoning": "Title derived from letter's content describing personal grief and location",
      "source_text": "Columbus Texas, June 16th 1858"
    },
    "creator": {
      "value": "Ringley",
      "confidence": "medium",
      "reasoning": "Signature appears at end of letter, though full name not clear",
      "source_text": "Ringley"
    },
    "subject": {
      "value": [
        "Family--Texas--19th century",
        "Grief--Personal narratives",
        "Child death--19th century"
      ],
      "authority": "lcsh",
      "confidence": "high",
      "reasoning": "Letter centers on personal tragedy involving loss of child",
      "source_text": "My little boy's body is still in the river",
      "alternative_headings": [
        "Loss (Psychology)",
        "Bereavement--Personal accounts"
      ]
    },
    "description": {
      "value": "Personal letter describing the traumatic loss of the author's young son, found in a river near Columbus, Texas, and the emotional impact on the family",
      "confidence": "high",
      "reasoning": "Summarizes key narrative elements of the letter",
      "source_text": "My little boy's body is still in the river... Grief is my portion of grief"
    },
    "date": {
      "value": "1858-06-16",
      "confidence": "high", 
      "reasoning": "Date clearly stated in letterhead",
      "source_text": "June 16th 1858"
    },
    "type": {
      "value": "Text",
      "qualifier": "Correspondence",
      "confidence": "high",
      "reasoning": "Handwritten personal letter"
    },
    "language": {
      "value": "en",
      "confidence": "high",
      "reasoning": "Letter written in English"
    },
    "coverage": {
      "spatial": ["Columbus, Texas", "Houston, Texas"],
      "temporal": "Mid-19th century",
      "confidence": "high",
      "reasoning": "Geographic locations explicitly mentioned in text",
      "source_text": "Columbus Texas, Houston"
    },
    "contributor": {
      "value": ["Unnamed recipient", "Prof.", "Re[illegible]"],
      "confidence": "medium",
      "reasoning": "Multiple references to recipients/acquaintances",
      "source_text": "Give my regards to the Prof."
    }
  },
  "additional_elements": {
    "source": {
      "value": "Personal correspondence collection",
      "confidence": "low",
      "reasoning": "No explicit collection information provided"
    },
    "rights": {
      "value": "Unknown",
      "confidence": "low",
      "reasoning": "No copyright or usage rights mentioned"
    }
  },
  "flags": {
    "ambiguous_dates": ["Burial date partially illegible"],
    "uncertain_attributions": ["Full name of sender unclear"],
    "requires_external_research": ["Precise provenance of letter"]
  }
}
```
```

Key observations:
1. The letter is a deeply personal account of child loss in mid-19th century Texas
2. Some textual elements are partially illegible, reducing confidence in certain metadata elements
3. Subject headings carefully selected to reflect emotional and historical context
4. Metadata aims to capture both factual and emotional dimensions of the document
============================================================
DUBLIN CORE METADATA ANALYSIS
============================================================

TITLE:
  Value: Personal Letter Describing Family Tragedy in Columbus, Texas
  Confidence: high
  Reasoning: Title derived from letter's content describing personal grief and location
  Source: "Columbus Texas, June 16th 1858"

CREATOR:
  Value: Ringley
  Confidence: medium
  Reasoning: Signature appears at end of letter, though full name not clear
  Source: "Ringley"

SUBJECT:
  Value: ['Family--Texas--19th century', 'Grief--Personal narratives', 'Child death--19th century']
  Confidence: high
  Reasoning: Letter centers on personal tragedy involving loss of child
  Source: "My little boy's body is still in the river"

DESCRIPTION:
  Value: Personal letter describing the traumatic loss of the author's young son, found in a river near Columbus, Texas, and the emotional impact on the family
  Confidence: high
  Reasoning: Summarizes key narrative elements of the letter
  Source: "My little boy's body is still in the river... Grief is my portion of grief"

DATE:
  Value: 1858-06-16
  Confidence: high
  Reasoning: Date clearly stated in letterhead
  Source: "June 16th 1858"

TYPE:
  Value: Text
  Confidence: high
  Reasoning: Handwritten personal letter

LANGUAGE:
  Value: en
  Confidence: high
  Reasoning: Letter written in English

CONTRIBUTOR:
  Value: ['Unnamed recipient', 'Prof.', 'Re[illegible]']
  Confidence: medium
  Reasoning: Multiple references to recipients/acquaintances
  Source: "Give my regards to the Prof."

==============================
ADDITIONAL ELEMENTS:
==============================

SOURCE:
  Personal correspondence collection (confidence: low)

RIGHTS:
  Unknown (confidence: low)

==============================
REVIEW REQUIRED:
==============================

Ambiguous Dates:
  • Burial date partially illegible

Uncertain Attributions:
  • Full name of sender unclear

Requires External Research:
  • Precise provenance of letter
Saved JSON metadata to: metadata_20250808_081208.json
Saved readable metadata to: metadata_20250808_081208.txt
Saved CSV metadata to: metadata_20250808_081208.csv
Cost Analysis:
Model: claude-3-5-haiku-20241022
Input tokens: 1,944
Output tokens: 889
Input cost: $0.001555
Output cost: $0.003556
Total cost: $0.005111
```
```
```
