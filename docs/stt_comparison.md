\# STT Comparison



\## Objective

Test and compare available Speech-to-Text services, then select a suitable solution for the project.



\## Tested Services

\- GLM ASR

\- Qwen ASR



\## Test Criteria

\- Chinese recognition accuracy

\- English recognition accuracy

\- Mixed-language recognition accuracy

\- Response speed

\- Stability

\- Suitability for Hong Kong multilingual context



\## Test Sentences

1\. 请帮我开始今天的阅读任务。

2\. I want to start the next activity.

3\. 我而家想 listen to the instructions.

4\. Please speak slower, 我未听清楚。

5\. 我们现在开始下一步，好吗？



\## Results Table

| Test Sentence | GLM ASR | Qwen ASR | Better Choice | Notes |

|---|---|---|---|---|

| 请帮我开始今天的阅读任务。 | Good | Good | Equal | Both handled simple Chinese well |

| I want to start the next activity. | Fair | Good | Qwen ASR | Qwen was clearer on English |

| 我而家想 listen to the instructions. | Fair | Better | Qwen ASR | Qwen handled mixed language better |

| Please speak slower, 我未听清楚。 | Fair | Better | Qwen ASR | Mixed language more stable in Qwen |

| 我们现在开始下一步，好吗？ | Good | Good | Equal | Both acceptable |



\## Summary

GLM ASR and Qwen ASR were both tested using Chinese, English, and mixed-language inputs.



Qwen ASR showed better performance in mixed-language recognition and English instructions.

GLM ASR was acceptable for simpler Chinese sentences.



\## Final Decision

\- Main STT: Qwen ASR

\- Backup STT: GLM ASR



\## Reason for Selection

Qwen ASR is selected as the main STT service because it performs better in mixed-language input and short spoken instructions, which are important for the project context.

