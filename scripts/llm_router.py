from dotenv import load_dotenv
import os

import json
from openai import OpenAI
from db_queries import (
    get_ac_year_stats_all,
    get_ac_year_stats_high_conf,
    get_top_affiliations_high_conf,
    get_ac_list_by_year,
    get_affiliation_trend,
    get_person_full_profile,
    find_persons_by_name,
    get_person_pub_venues,
    get_coauthors_for_person,
    smart_person_lookup,
    get_ac_year_overview,
    get_trend_overview,
    get_top_countries_overall,
)
load_dotenv(override=True)
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)
# ===================== Style Samples =====================

SAMPLE_TEXT = """
===== SAMPLE 1 =====
In the more recent years, HCI papers seem less likely to be cited by papers outside of the core HCI venues.
The previous analysis suggests that we can aggregate each year’s citations of HCI papers so that we can see how the non-HCI papers’ interest in citing HCI papers changed over the years. For each year, we consider that year’s citations of HCI papers published in previous five years. Since we do not have citation information before 2010, our analysis can only begin from 2015. The results exhibit a decreasing pattern over the years. In other words, in the more recent years, HCI papers seem less likely to be cited by papers outside of our core HCI venue list.

===== SAMPLE 2 =====
Amongst all HCI papers cited in a given year, the earlier-published papers were cited more outside of the core HCI venues.
To expand our analysis along the time dimension, we plot each year’s published HCI papers’ citations by non-HCI venues over the subsequent years. Note that the x-axis is now citation year, not publication year. The results show that, for most years’ HCI papers, the ratio of non-HCI citations tends to flatten or slightly decrease over time, except for a few local cases. Further, amongst HCI papers cited in a given citation year, the earlier papers tend to have attracted more non-HCI citations than the later ones.

===== SAMPLE 3 =====
CSCW and Scientific Practices.
Earlier studies quantitatively examined the CSCW literature by tracing citation counts over time and mapping collaboration networks. One line of work analyzed thousands of citations to assess the impact of CSCW research over several years, revealing relatively stable citation volumes during the 1990s. Co-authorship network analyses showed that CSCW authors maintained strong collaborations with researchers in other fields, although physical proximity still played a major role in enabling joint work. Other studies focused on the demographics of CSCW conferences, showing a high proportion of contributions from US-based academics compared to European researchers, and highlighting a sustained emphasis on group issues and system design. Subsequent scientometric analyses identified a stable share of design and evaluation studies, a decline in non-empirical work, and an increasing use of experiments and ethnographic methods.
"""

# ===================== System Prompt =====================

SYSTEM_PROMPT = (
    "You are an HCI / scientometrics researcher and narrative writer.\n"
    "You write short, story-like analysis subsections based ONLY on the "
    "structured data I give you from a CHI AC database.\n\n"
    "WRITING FORMAT (MANDATORY):\n"
    "- Final answer must be a short scientometrics subsection with:\n"
    "  1) a TITLE (one line, evocative but concise),\n"
    "  2) then exactly two narrative paragraphs (about 200–260 words total),\n"
    "  3) and finally ONE line of research keywords.\n"
    "- Paragraph 1: broader trend or context that relates to the question.\n"
    "- Paragraph 2: zoom into one or two concrete examples "
    "(e.g., one AC, one institution, one committee, or one year).\n"
    "- Each answer must include at least THREE concrete facts "
    "(years, venues, roles, counts, institutions, or paper titles) "
    "that appear in the structured data.\n"
    "- After the two paragraphs, add one line in the form:\n"
    "  KEYWORDS: keyword1; keyword2\n"
    "  where each keyword is a short English research keyword (1–3 words), "
    "  capturing the main critical angle of the subsection (e.g., "
    "  'AC diversity', 'institutional concentration').\n\n"
    "STYLE:\n"
    "- Tone similar to the style samples: scientometric, interpretive, slightly story-like.\n"
    "- You may use light metaphors (currents, clusters, trajectories) but stay grounded.\n"
    "- No bullet points, no numbered lists.\n"
    "- Do NOT mention JSON, schemas, tools, or databases.\n"
    "- Do NOT mention 'high confidence' or any internal labels.\n"
)


# ===================== Tool definitions =====================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_trend_overview",
            "description": "Global trend overview: yearly AC counts, top affiliations, top countries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "high_conf_only": {
                        "type": "boolean",
                        "default": True,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ac_year_overview",
            "description": "Overview for a single year: total ACs, country distribution, committee distribution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "high_conf_only": {
                        "type": "boolean",
                        "default": True,
                    },
                },
                "required": ["year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_countries_overall",
            "description": "Global distribution of ACs by country (top N).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 20,
                    },
                    "high_conf_only": {
                        "type": "boolean",
                        "default": True,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ac_year_stats_all",
            "description": "Raw total number of ACs per year (all persons).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ac_year_stats_high_conf",
            "description": "Raw yearly AC counts for DBLP-matched ACs.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_affiliations_high_conf",
            "description": "Top affiliations among DBLP-matched ACs, by AC-role count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max number of affiliations to return.",
                        "default": 20,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ac_list_by_year",
            "description": "List ACs for a given year.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "high_conf_only": {
                        "type": "boolean",
                        "description": "If true, only include DBLP-matched ACs.",
                        "default": False,
                    },
                },
                "required": ["year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_affiliation_trend",
            "description": "AC counts per year for a given affiliation keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "high_conf_only": {
                        "type": "boolean",
                        "default": True,
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_person_full_profile",
            "description": "Get full AC + publication profile for one person_id.",
            "parameters": {
                "type": "object",
                "properties": {"person_id": {"type": "integer"}},
                "required": ["person_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_persons_by_name",
            "description": "Find persons whose canonical_name contains a substring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_substring": {"type": "string"},
                    "high_conf_only": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["name_substring"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_person_pub_venues",
            "description": "For a person_id, count publications per venue.",
            "parameters": {
                "type": "object",
                "properties": {"person_id": {"type": "integer"}},
                "required": ["person_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_coauthors_for_person",
            "description": "Return coauthors of a given person_id and coauthored paper counts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "person_id": {"type": "integer"},
                    "limit": {
                        "type": "integer",
                        "default": 50,
                    },
                },
                "required": ["person_id"],
            },
        },
    },
    {
    "type": "function",
    "function": {
        "name": "smart_person_lookup",
        "description": "Find a person by name, then automatically fetch their profile and publications.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Person name or substring to search for."
                }
            },
            "required": ["name"]
        }
    }
    },
    {
        "type": "function",
        "function": {
            "name": "get_summary_snapshot",
            "description": "Legacy global snapshot; similar to get_trend_overview.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# ===================== Local tool runner =====================

def _call_local_tool(name: str, arguments: dict):
    if name == "get_trend_overview":
        return get_trend_overview(**arguments)
    if name == "get_ac_year_overview":
        return get_ac_year_overview(**arguments)
    if name == "get_top_countries_overall":
        return get_top_countries_overall(**arguments)
    if name == "get_ac_year_stats_all":
        return get_ac_year_stats_all()
    if name == "get_ac_year_stats_high_conf":
        return get_ac_year_stats_high_conf()
    if name == "get_top_affiliations_high_conf":
        return get_top_affiliations_high_conf(**arguments)
    if name == "get_ac_list_by_year":
        return get_ac_list_by_year(**arguments)
    if name == "get_affiliation_trend":
        return get_affiliation_trend(**arguments)
    if name == "get_person_full_profile":
        return get_person_full_profile(**arguments)
    if name == "find_persons_by_name":
        return find_persons_by_name(**arguments)
    if name == "get_person_pub_venues":
        return get_person_pub_venues(**arguments)
    if name == "get_coauthors_for_person":
        return get_coauthors_for_person(**arguments)
    if name == "smart_person_lookup":
        return smart_person_lookup(**arguments)
    raise ValueError(f"Unknown tool {name}")

# ===================== Main entry =====================

def answer_with_db_tools(user_query: str) -> str:
    collected: dict[str, list[dict]] = {}

    # ---------- preprocessing ----------
    person_hits = find_persons_by_name(
        name_substring=user_query,
        high_conf_only=True,
        limit=5,
    )
    if person_hits:
        collected["find_persons_by_name"] = [
            {
                "args": {
                    "name_substring": user_query,
                    "high_conf_only": True,
                    "limit": 5,
                },
                "result": person_hits,
            }
        ]

        main_person_id = person_hits[0]["person_id"]

        full_profile = get_person_full_profile(main_person_id) or {}
        venues = get_person_pub_venues(main_person_id) or []

        collected["get_person_full_profile"] = [
            {
                "args": {"person_id": main_person_id},
                "result": full_profile,
            }
        ]
        collected["get_person_pub_venues"] = [
            {
                "args": {"person_id": main_person_id},
                "result": venues,
            }
        ]

    # ---------- planning ----------
    planning_messages = [
        {
            "role": "system",
            "content": (
                "You are a planner that decides which tools to call on a CHI AC database. "
                "In THIS STEP you must NOT answer the user. "
                "Your only job is to return tool_calls with appropriate arguments.\n"
                "Prefer aggregated tools like get_trend_overview and get_ac_year_overview "
                "over very detailed lists to keep outputs small.\n"
                "If the user query mentions a specific person (e.g., “tell me papers of…”, “interesting paper of …”),"
                "ALWAYS use the tool smart_person_lookup(name=...) to retrieve both identity and publications."
                "Never stop after finding the name only."

            ),
        },
        {
            "role": "user",
            "content": (
                f"User question:\n{user_query}\n\n"
                "Decide which additional tools to call to gather data needed to answer this question.\n"
                "Note: person search may have already been run in Python; you can still call "
                "other tools for trends, years, or affiliations.\n"
                "Return ONLY tool_calls, no natural language explanation."
            ),
        },
    ]

    plan_resp = client.chat.completions.create(
        model="gpt-5-mini",
        messages=planning_messages,
        tools=TOOLS,
        tool_choice="auto",
    )
    plan_msg = plan_resp.choices[0].message

    if getattr(plan_msg, "tool_calls", None):
        for tc in plan_msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            result = _call_local_tool(name, args)

            bucket = collected.setdefault(name, [])
            bucket.append(
                {
                    "args": args,
                    "result": result,
                }
            )

    if not collected:
        collected["get_trend_overview"] = [
            {
                "args": {"high_conf_only": True},
                "result": get_trend_overview(True),
            }
        ]

    db_context_json = json.dumps(collected, ensure_ascii=False, indent=2)

    final_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "USER QUESTION:\n"
                f"{user_query}\n\n"
                "STRUCTURED DATA FROM DATABASE (source of truth, DO NOT COPY OR QUOTE DIRECTLY):\n"
                f"{db_context_json}\n\n"
                "TASK STYLE:\n"
                "- Always answer as a short scientometrics subsection.\n"
                "- Output format:\n"
                "  1) First line: a short, evocative TITLE.\n"
                "  2) Then TWO paragraphs (~200–260 words total).\n"
                "  3) Finally ONE line of critical research keywords in the form:\n"
                "     KEYWORDS: keyword1; keyword2\n"
                "- Use ONLY facts that appear in the structured data above.\n"
                "- No bullet points. No mention of tools or databases.\n"
                "- Start directly with the TITLE (no preamble).\n\n"
                "STYLE REFERENCE (for tone and rhythm only, do NOT copy wording):\n"
                f"{SAMPLE_TEXT}\n"
            ),
        },
    ]

    final_resp = client.chat.completions.create(
        model="gpt-5-mini",
        messages=final_messages,
    )
    return final_resp.choices[0].message.content or ""
