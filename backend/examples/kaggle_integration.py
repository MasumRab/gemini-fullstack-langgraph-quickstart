"""Kaggle Models Integration Scaffolding.

This module provides reference implementations for downloading and integrating
models from Kaggle (https://www.kaggle.com/models) into the agent architecture.

It handles:
1. Model downloading via `kagglehub`.
2. Adaptation to the `LLMClient` interface.
3. A basic ReAct (Reasoning + Acting) loop to enable tool use for standard text-gen models.

Prerequisites:
    pip install kagglehub transformers torch accelerate
"""

import os
import re
from typing import Any, List


# Define a base LLM interface compatible with the project
class BaseLLMClient:
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError

class KaggleModelLoader:
    """Helper to download and load models from Kaggle."""

    @staticmethod
    def download(handle: str, path: str | None = None) -> str:
        """Download a model from Kaggle.

        Args:
            handle: Kaggle model handle (e.g., 'google/gemma/pyTorch/2b').
            path: Optional local path to download to.

        Returns:
            The local path to the downloaded model weights.
        """
        try:
            import kagglehub
        except ImportError:
            raise ImportError("Please install 'kagglehub': pip install kagglehub")

        print(f"Downloading model: {handle}...")
        model_path = kagglehub.model_download(handle, path=path)
        print(f"Model downloaded to: {model_path}")
        return model_path

class KaggleHuggingFaceClient(BaseLLMClient):
    """Adapter for Kaggle models compatible with Hugging Face Transformers.

    This is useful for models like Gemma, Llama, Mistral available on Kaggle
    in PyTorch/Transformers format.
    """

    def __init__(self, model_handle: str, device: str = "auto"):
        """Initialize the client.

        Args:
            model_handle: Kaggle model handle or local path.
            device: 'auto', 'cuda', or 'cpu'.
        """
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError:
            raise ImportError("Please install 'transformers' and 'torch'.")

        # 1. Download/Resolve path
        if not os.path.exists(model_handle):
            self.model_path = KaggleModelLoader.download(model_handle)
        else:
            self.model_path = model_handle

        print(f"Loading model from {self.model_path}...")

        # 2. Load Tokenizer & Model
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            device_map=device,
            torch_dtype="auto"
        )

    def generate(self, prompt: str, max_new_tokens: int = 512, **kwargs) -> str:
        """Generate text."""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=kwargs.get("temperature", 0.0) > 0,
            temperature=kwargs.get("temperature", 0.7),
        )

        # Decode only the new tokens
        generated_text = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        return generated_text

class SimpleReActAgent:
    """A simple ReAct (Reason+Act) wrapper to enable tool use for
    plain text-generation models downloaded from Kaggle.

    This replaces the native function calling capabilities of API-based models.
    """

    REACT_PROMPT_TEMPLATE = """
You are a helpful assistant. You have access to the following tools:

{tool_descriptions}

To use a tool, please use the following format:

Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (json format)
Observation: the result of the action

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

Thought: Do I need to use a tool? No
Final Answer: [your response here]

Begin!

User: {input}
"""

    def __init__(self, llm: BaseLLMClient, tools: List[Any]):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.tool_descriptions = "\n".join([f"{t.name}: {t.description}" for t in tools])
        self.tool_names = ", ".join([t.name for t in tools])

    def run(self, user_input: str, max_steps: int = 5) -> str:
        """Execute the ReAct loop."""
        history = self.REACT_PROMPT_TEMPLATE.format(
            tool_descriptions=self.tool_descriptions,
            tool_names=self.tool_names,
            input=user_input
        )

        for i in range(max_steps):
            # 1. Generate thought/action
            response = self.llm.generate(history, stop=["Observation:"])
            history += response

            # 2. Parse Action
            action_match = re.search(r"Action: (.*?)[\n\r]+Action Input: (.*)", response, re.DOTALL)

            if "Final Answer:" in response:
                return response.split("Final Answer:")[-1].strip()

            if action_match:
                action_name = action_match.group(1).strip()
                action_input = action_match.group(2).strip()

                # 3. Execute Tool
                observation = f"\nObservation: Tool '{action_name}' not found."
                if action_name in self.tools:
                    try:
                        # Assumption: tools are LangChain tools or similar callables
                        tool_output = self.tools[action_name].invoke(action_input)
                        observation = f"\nObservation: {tool_output}"
                    except Exception as e:
                        observation = f"\nObservation: Error: {str(e)}"

                history += observation
            else:
                # If model failed to follow format, try to prompt it again or stop
                history += "\nObservation: Invalid format. Please use 'Action:' and 'Action Input:'."

        return "Agent stopped due to iteration limit."

# Example Usage Mock
if __name__ == "__main__":
    # This block allows manual testing if dependencies are installed
    try:
        # Mock Tool
        class MockTool:
            name = "calculator"
            description = "Calculates math expressions"
            def invoke(self, input_str):
                # Use a safe math expression evaluator instead of eval()
                import ast
                import operator as op
                operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                             ast.Div: op.truediv, ast.Pow: op.pow,
                             ast.UnaryOp: op.neg}
                
                def _eval(node):
                    if isinstance(node, ast.Constant):
                        return node.value
                    elif isinstance(node, ast.BinOp):
                        return operators[type(node.op)](_eval(node.left), _eval(node.right))
                    elif isinstance(node, ast.UnaryOp):
                        return operators[type(node.op)](_eval(node.operand))
                    else:
                        raise TypeError(f"Unsupported node type: {type(node)}")

                try:
                    # Strip any potential quotes if model passed it as string
                    input_str = input_str.strip("'\"")
                    result = _eval(ast.parse(input_str, mode='eval').body)
                    return str(result)
                except Exception as e:
                    return f"Error evaluating expression: {str(e)}"

        print("This module provides scaffolding. To run a real test, install kagglehub and transformers.")
        # client = KaggleHuggingFaceClient("google/gemma/pyTorch/2b-it")
        # agent = SimpleReActAgent(client, [MockTool()])
        # print(agent.run("What is 20 * 5?"))

    except ImportError:
        print("Dependencies missing. Run: pip install kagglehub transformers torch")
