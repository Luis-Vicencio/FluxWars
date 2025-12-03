# LLM AI Setup for FluxWars

The Expert difficulty AI uses Large Language Models (LLMs) for strategic game reasoning.

## Quick Start

### Option 1: OpenAI (Recommended)

1. Get an API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set environment variable:
   ```bash
   export OPENAI_API_KEY="sk-your-key-here"
   ```
3. Install OpenAI library:
   ```bash
   pip install openai
   ```

### Option 2: Anthropic Claude

1. Get an API key from [Anthropic Console](https://console.anthropic.com/)
2. Set environment variables:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-your-key-here"
   export LLM_PROVIDER="anthropic"
   export LLM_MODEL="claude-3-sonnet-20240229"
   ```
3. Install Anthropic library:
   ```bash
   pip install anthropic
   ```

## Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key
- `ANTHROPIC_API_KEY` - Your Anthropic API key  
- `LLM_PROVIDER` - Provider to use: `openai` (default) or `anthropic`
- `LLM_MODEL` - Model to use:
  - OpenAI: `gpt-4` (default), `gpt-3.5-turbo`
  - Anthropic: `claude-3-sonnet-20240229`, `claude-3-opus-20240229`

## Usage

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. In the game settings, select **Expert** difficulty

3. The AI will:
   - Serialize the current game state to text
   - Send it to the LLM with strategic context
   - Parse the LLM's suggested move
   - Execute the move on the board
   - Fall back to MCTS if LLM fails

## How It Works

1. **State Serialization**: Converts board, polarities, and clusters to readable text
2. **Strategic Prompt**: Adds game rules and strategic considerations
3. **LLM Reasoning**: Model analyzes board and suggests best move
4. **Response Parsing**: Extracts move coordinates and direction from LLM response
5. **Execution**: Applies the move and uses heuristics for remaining dice

## Fallback Behavior

If LLM is unavailable (no API key, network error, parsing failure), the Expert AI automatically falls back to MCTS (Normal difficulty) to ensure gameplay continues.

## Cost Considerations

- OpenAI GPT-4: ~$0.03 per move
- OpenAI GPT-3.5-Turbo: ~$0.001 per move  
- Anthropic Claude: ~$0.015 per move

Consider using GPT-3.5-Turbo for development/testing.

## Testing

Test the LLM AI without playing:

```bash
# Set your API key first
export OPENAI_API_KEY="your-key"

# Run test
python test_llm.py
```

## Troubleshooting

**"No API key found"**
- Make sure you've exported the environment variable in your current shell
- Check spelling: `echo $OPENAI_API_KEY`

**"Missing library"**
- Install required package: `pip install openai` or `pip install anthropic`

**"API call failed"**
- Verify your API key is valid
- Check your account has credits/billing enabled
- Ensure you have internet connectivity

**"Failed to parse valid move"**
- LLM response didn't match expected format
- Game falls back to MCTS automatically
- Check console logs for LLM response text
