import logging

logger = logging.getLogger("app")

# Rates per 1,000,000 (1M) tokens
PRICING_MAP = {
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "default": {"input": 1.50, "output": 2.00}
    },
    "groq": {
        "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
        "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
        "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
        "default": {"input": 0.10, "output": 0.15}
    },
    "lm_studio": {
        "default": {"input": 0.00, "output": 0.00}
    }
}

class CostCalculator:
    """
    Utility to calculate the token cost for LLM executions based on provider and model pricing.
    """
    
    @staticmethod
    def calculate(provider: str, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculates LLM cost based on input/output tokens and pricing configurations.
        
        Args:
            provider: The API provider (groq, openai, lm_studio).
            model_name: Name/identifier of the model.
            prompt_tokens: Number of prompt/input tokens.
            completion_tokens: Number of completion/output tokens.
            
        Returns:
            Calculated cost in USD (float).
        """
        if not provider or not model_name:
            logger.warning("CostCalculator: Missing provider or model name. Defaulting cost to $0.00")
            return 0.0
            
        prov = provider.lower().strip()
        model = model_name.lower().strip()
        
        # Local model is free
        if prov in ["lm_studio", "lmstudio", "local"]:
            logger.info("CostCalculator: Local provider detected. Cost is $0.00")
            return 0.0
            
        # Match provider pricing
        provider_pricing = PRICING_MAP.get(prov)
        if not provider_pricing:
            # Fallback to general/unknown provider pricing
            logger.warning(f"CostCalculator: Unknown provider '{provider}'. Defaulting to $0.00 cost calculation.")
            return 0.0
            
        # Match model pricing
        rates = None
        for key in provider_pricing:
            if key != "default" and key in model:
                rates = provider_pricing[key]
                break
                
        if not rates:
            rates = provider_pricing.get("default", {"input": 0.0, "output": 0.0})
            logger.info(f"CostCalculator: No specific pricing rates found for model '{model_name}'. Using provider defaults: {rates}")
            
        # Calculation: (tokens / 1,000,000) * rate
        input_cost = (prompt_tokens / 1_000_000.0) * rates["input"]
        output_cost = (completion_tokens / 1_000_000.0) * rates["output"]
        total_cost = round(input_cost + output_cost, 6)
        
        logger.info(
            f"CostCalculator: provider={prov} model={model} | "
            f"prompt_tokens={prompt_tokens} (cost=${input_cost:.6f}) | "
            f"completion_tokens={completion_tokens} (cost=${output_cost:.6f}) | "
            f"total_cost=${total_cost:.6f}"
        )
        return total_cost
