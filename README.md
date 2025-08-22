# Experimental Tools for Sesquicentennial Workflows

The repository here includes experimental tools for generating hand written text and metadata about handwritten
documents for Sesquicentennial related works.

This is a work in progress but the idea is to write prompts as markdown (you can see those in `prompts`) and use Claude for HTR
and metadata generation.

## Sample Output of a Handwritten, Multi Page Letter using claude-3-5-haiku-20241022

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


## Sample of a Handwritten, Multi Page Letter Using Claude 4 Sonnet

```
```
```
Extracted text:
Columbus Texas
June 16th 1858

Dear M[illegible],

Though I feel very little alike writing you I much use you the condition I am in and the feelings I experience this eve be nothing more than a note. The news consisted in Houston, and I at would softly at home yesterday, at 2:10 9'mc. As I anticipated I found my father in the coldest state of excitement, and the deepest chars of sorrow agony. Tears with the greatest effort of my life that I controlled my overflowing grief sufficiently to become a comforter to him. At time, I may comfort him to some extent; myself to none. Grief is my portion of grief. I must bear. My little boys baby is still in the river or - but [illegible]

not speak of the horrible thought! They have vainly sought the dear childly though now hopeless, in every place & manner. at first like a man adrift, yet I know I'm not penniless. In this I will send the rumination merely of my feelings. Please hand them in submitting the necessary remarks. Chanced it so happens that you leave before my return don't forget to give the key to the Bearer.

I must return the last of this week but cannot if matters remain as they now are.

I know that you appreciate my feelings enough to think nothing more of this futile attempt at commencing a letter. Give my regards to the Prof. especially our friend Dr. otherwise a medium through which I may send such matter, so may go the young ladies. Enough for the present.

Kindly

Tuesday the 18th on the day of punishing the storm were terrible, but was found in the river, some fifteen miles below. Some in a frightful condition, but we managed to get him home and provided matted. The rumored occurred yesterday morning at 10 o'clock. No notice of a funeral were notified but many persons were cut to witness the burial of my boy - then interred, now I hope safely at. Justice seems better reconciled since the recovery & burial of his little boy.

I shall be the last of next week before I can return to the College then to remain not long. If you know of anything you want of me let me know by letter, or it it comes to your mind for late for that leave me a note on our table. Kindly

==================================================

```
```
{
  "dublin_core": {
    "title": {
      "value": "Letter regarding the drowning death of a child in Columbus, Texas",
      "confidence": "medium",
      "reasoning": "No explicit title exists; constructed descriptive title based on main content theme",
      "source_text": "My little boys baby is still in the river... but was found in the river, some fifteen miles below... the burial of my boy"
    },
    "creator": {
      "value": "Unknown",
      "confidence": "low",
      "reasoning": "Letter is signed only with 'Kindly' which appears to be a closing rather than a signature; sender's name is not clearly identifiable",
      "source_text": "Kindly"
    },
    "subject": {
      "value": ["Death", "Drowning", "Grief", "Children--Death", "Texas--History--19th century"],
      "authority": "lcsh",
      "confidence": "medium",
      "reasoning": "Selected LCSH terms based on the central themes of child death by drowning and grief. Standard LCSH format used for subdivisions.",
      "source_text": "My little boys baby is still in the river... deepest chars of sorrow agony... Grief is my portion of grief... but was found in the river... the burial of my boy",
      "alternative_headings": ["Family--Death", "Accidents"],
      "authorization_uncertain": ["Children--Death"]
    },
    "description": {
      "value": "Personal letter from Columbus, Texas describing the tragic drowning death of the writer's young son. The letter expresses profound grief and describes the search for and eventual recovery of the child's body from the river. Written during a time of family crisis and emotional distress.",
      "confidence": "high",
      "reasoning": "Clear narrative thread about child's drowning death, recovery of body, and burial",
      "source_text": "My little boys baby is still in the river... They have vainly sought the dear childly... but was found in the river, some fifteen miles below... the burial of my boy"
    },
    "date": {
      "value": "1858-06-16",
      "confidence": "high",
      "reasoning": "Date clearly stated at beginning of letter",
      "source_text": "June 16th 1858"
    },
    "type": {
      "value": "Text",
      "qualifier": "Correspondence",
      "confidence": "high",
      "reasoning": "Format is clearly a personal letter with salutation, body, and closing"
    },
    "language": {
      "value": "en",
      "confidence": "high",
      "reasoning": "Letter written in English throughout"
    },
    "coverage": {
      "spatial": ["Columbus (Tex.)", "Houston (Tex.)"],
      "temporal": "1858",
      "confidence": "high",
      "reasoning": "Columbus, Texas mentioned as location at letter head; Houston referenced in content",
      "source_text": "Columbus Texas... The news consisted in Houston"
    },
    "contributor": {
      "value": ["Unknown recipient (M[illegible])", "Father (mentioned)", "Prof. (mentioned)", "Dr. (mentioned)"],
      "confidence": "low",
      "reasoning": "Recipient's name is illegible; other persons mentioned but not fully identified",
      "source_text": "Dear M[illegible]... Give my regards to the Prof. especially our friend Dr."
    }
  },
  "additional_elements": {
    "publisher": {
      "value": "Not specified",
      "confidence": "low",
      "reasoning": "No repository or holding institution mentioned in the letter text"
    },
    "identifier": {
      "value": "Not specified",
      "confidence": "low",
      "reasoning": "No catalog numbers or institutional identifiers present in the text"
    },
    "source": {
      "value": "Not specified",
      "confidence": "low",
      "reasoning": "No collection or provenance information provided in the letter text"
    },
    "relation": {
      "value": "Not specified",
      "confidence": "low",
      "reasoning": "No explicit references to other documents or series mentioned"
    },
    "rights": {
      "value": "Not specified",
      "confidence": "low",
      "reasoning": "No copyright or access information determinable from letter content"
    },
    "format": {
      "value": "Not specified",
      "confidence": "low",
      "reasoning": "Physical format not described in the provided text"
    }
  },
  "flags": {
    "ambiguous_dates": ["Tuesday the 18th - unclear which month/year but likely June 18, 1858"],
    "uncertain_attributions": ["Creator identity unknown", "Recipient name illegible", "Mentioned persons not fully identified"],
    "uncertain_lcsh_authorization": ["Children--Death may need verification against current authorized format"],
    "requires_external_research": ["Creator identification", "Recipient identification", "Historical context of Columbus, Texas in 1858"],
    "alternative_subjects": ["Family correspondence", "Personal narratives", "Nineteenth century Texas"]
  }
}
```
```
============================================================
DUBLIN CORE METADATA ANALYSIS
============================================================

TITLE:
  Value: Letter regarding the drowning death of a child in Columbus, Texas
  Confidence: medium
  Reasoning: No explicit title exists; constructed descriptive title based on main content theme
  Source: "My little boys baby is still in the river... but was found in the river, some fifteen miles below......"

CREATOR:
  Value: Unknown
  Confidence: low
  Reasoning: Letter is signed only with 'Kindly' which appears to be a closing rather than a signature; sender's name is not clearly identifiable
  Source: "Kindly"

SUBJECT:
  Value: ['Death', 'Drowning', 'Grief', 'Children--Death', 'Texas--History--19th century']
  Confidence: medium
  Reasoning: Selected LCSH terms based on the central themes of child death by drowning and grief. Standard LCSH format used for subdivisions.
  Source: "My little boys baby is still in the river... deepest chars of sorrow agony... Grief is my portion of..."

DESCRIPTION:
  Value: Personal letter from Columbus, Texas describing the tragic drowning death of the writer's young son. The letter expresses profound grief and describes the search for and eventual recovery of the child's body from the river. Written during a time of family crisis and emotional distress.
  Confidence: high
  Reasoning: Clear narrative thread about child's drowning death, recovery of body, and burial
  Source: "My little boys baby is still in the river... They have vainly sought the dear childly... but was fou..."

DATE:
  Value: 1858-06-16
  Confidence: high
  Reasoning: Date clearly stated at beginning of letter
  Source: "June 16th 1858"

TYPE:
  Value: Text
  Confidence: high
  Reasoning: Format is clearly a personal letter with salutation, body, and closing

LANGUAGE:
  Value: en
  Confidence: high
  Reasoning: Letter written in English throughout

CONTRIBUTOR:
  Value: ['Unknown recipient (M[illegible])', 'Father (mentioned)', 'Prof. (mentioned)', 'Dr. (mentioned)']
  Confidence: low
  Reasoning: Recipient's name is illegible; other persons mentioned but not fully identified
  Source: "Dear M[illegible]... Give my regards to the Prof. especially our friend Dr."

==============================
ADDITIONAL ELEMENTS:
==============================

PUBLISHER:
  Not specified (confidence: low)

IDENTIFIER:
  Not specified (confidence: low)

SOURCE:
  Not specified (confidence: low)

RELATION:
  Not specified (confidence: low)

RIGHTS:
  Not specified (confidence: low)

FORMAT:
  Not specified (confidence: low)

==============================
REVIEW REQUIRED:
==============================

Ambiguous Dates:
  • Tuesday the 18th - unclear which month/year but likely June 18, 1858

Uncertain Attributions:
  • Creator identity unknown
  • Recipient name illegible
  • Mentioned persons not fully identified

Uncertain Lcsh Authorization:
  • Children--Death may need verification against current authorized format

Requires External Research:
  • Creator identification
  • Recipient identification
  • Historical context of Columbus, Texas in 1858

Alternative Subjects:
  • Family correspondence
  • Personal narratives
  • Nineteenth century Texas
Saved JSON metadata to: metadata_20250812_170119.json
Saved readable metadata to: metadata_20250812_170119.txt
Saved CSV metadata to: metadata_20250812_170119.csv
Cost Analysis:
Model: claude-sonnet-4-20250514
Input tokens: 1,944
Output tokens: 1,249
Input cost: $0.005832
Output cost: $0.018735
Total cost: $0.024567
```
```
```


## Sample Output of an AV work based on contents of a WebVTT file and claude-3-5-haiku-20241022

```
```
```
Sample output:
```
```
{
  "content_analysis": {
    "media_type": "audio",
    "content_category": "interview",
    "primary_content_summary": "Interview with science fiction author Kevin O'Donnell, Jr. discussing his writing career, novels, and experiences",
    "speakers_identified": ["Kevin O'Donnell, Jr.", "Interviewer"],
    "key_topics_mentioned": [
      "Science fiction writing", 
      "Novel writing process", 
      "Literary influences", 
      "Science fiction genres", 
      "Alien cultures"
    ],
    "dates_referenced": ["1966", "1972", "1973", "1974", "1975", "1976"],
    "locations_mentioned": ["Cleveland", "Seoul", "Korea", "New Haven", "Yale"],
    "duration_estimate": "Approximately 48 minutes"
  },
  "avalon_mods_metadata": {
    "required_fields": {
      "title": {
        "value": "Kevin O'Donnell, Jr. Interview",
        "confidence": "high",
        "reasoning": "Standard interview title format",
        "source_segments": ["The tape is rolling, so it's all on record now."]
      },
      "date_issued": {
        "value": "2025-07-08",
        "confidence": "high",
        "reasoning": "Date from WebVTT file metadata",
        "source_segments": ["File Creation Date: 2025-07-08"]
      }
    },
    "core_descriptive": {
      "main_contributor_creator": {
        "value": ["O'Donnell, Kevin, Jr."],
        "authority": "lcnaf",
        "confidence": "high",
        "reasoning": "Primary subject of the interview",
        "source_segments": ["The entire transcript is about Kevin O'Donnell, Jr."]
      },
      "contributor": {
        "value": ["Unnamed Interviewer"],
        "confidence": "medium",
        "reasoning": "Interviewer is present but not identified by name"
      },
      "genre": {
        "value": ["Oral histories", "Author interviews"],
        "authority": "lcsh",
        "confidence": "high"
      },
      "publisher": {
        "value": "Texas A&M University Libraries",
        "confidence": "high",
        "source_segments": ["Responsible Party: US, Texas A&M University Libraries"]
      },
      "summary_abstract": {
        "value": "In-depth interview with science fiction author Kevin O'Donnell, Jr. discussing his writing career, novels including Bandersnatch and McGill Feighan series, and literary influences.",
        "confidence": "high"
      },
      "language": {
        "value": ["eng"],
        "authority": "marc",
        "confidence": "high"
      }
    },
    "subject_access": {
      "topical_subject": {
        "value": [
          "Science fiction literature",
          "Authors, American",
          "Science fiction writing"
        ],
        "authority": "lcsh",
        "confidence": "high"
      },
      "geographic_subject": {
        "value": ["United States"],
        "authority": "tgn",
        "confidence": "high"
      }
    },
    "additional_fields": {
      "notes": [
        {
          "note_type": "biographical/historical",
          "note_value": "Interview discusses O'Donnell's development as a science fiction writer, including early influences and writing process",
          "confidence": "high"
        }
      ]
    }
  }
}
```
```

The metadata captures the key details of this interview with science fiction author Kevin O'Donnell, Jr., following Avalon's MODS metadata schema and utilizing appropriate controlled vocabularies.
============================================================
AVALON MODS METADATA ANALYSIS
============================================================

CONTENT ANALYSIS:
  Media Type: audio
  Content Category: interview
  Duration Estimate: Approximately 48 minutes
  Primary Content: Interview with science fiction author Kevin O'Donnell, Jr. discussing his writing career, novels, and experiences
  Speakers: Kevin O'Donnell, Jr., Interviewer
  Key Topics: Science fiction writing, Novel writing process, Literary influences, Science fiction genres, Alien cultures

==============================
REQUIRED FIELDS:
==============================

TITLE:
  Value: Kevin O'Donnell, Jr. Interview
  Confidence: high
  Reasoning: Standard interview title format

DATE ISSUED:
  Value: 2025-07-08
  Confidence: high
  Reasoning: Date from WebVTT file metadata

==============================
CORE DESCRIPTIVE FIELDS:
==============================

MAIN CONTRIBUTOR CREATOR:
  Value: O'Donnell, Kevin, Jr.
  Confidence: high
  Authority: lcnaf
  Reasoning: Primary subject of the interview

CONTRIBUTOR:
  Value: Unnamed Interviewer
  Confidence: medium
  Reasoning: Interviewer is present but not identified by name

GENRE:
  Value: Oral histories; Author interviews
  Confidence: high
  Authority: lcsh

PUBLISHER:
  Value: Texas A&M University Libraries
  Confidence: high

SUMMARY ABSTRACT:
  Value: In-depth interview with science fiction author Kevin O'Donnell, Jr. discussing his writing career, novels including Bandersnatch and McGill Feighan series, and literary influences.
  Confidence: high

LANGUAGE:
  Value: eng
  Confidence: high
  Authority: marc

==============================
SUBJECT ACCESS:
==============================

TOPICAL SUBJECT:
  Value: Science fiction literature; Authors, American; Science fiction writing
  Confidence: high
  Authority: lcsh

GEOGRAPHIC SUBJECT:
  Value: United States
  Confidence: high
  Authority: tgn

==============================
ADDITIONAL FIELDS:
==============================

NOTES:
  Biographical/Historical: Interview discusses O'Donnell's development as a science fiction writer, including early influences and writing process
Saved JSON metadata to: metadata_20250812_190636.json
Saved readable metadata to: metadata_20250812_190636.txt
Saved CSV metadata to: metadata_20250812_190636.csv
Cost Analysis:
Model: claude-3-5-haiku-20241022
Input tokens: 15,134
Output tokens: 959
Input cost: $0.012107
Output cost: $0.003836
Total cost: $0.015943
```
```
```