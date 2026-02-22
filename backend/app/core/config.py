from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartBiz AI Backend"
    # Pydantic will automatically look for DATABASE_URL in the .env file
    DATABASE_URL: str 
    
    # This tells the class where to find your variables
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# This creates the exact 'settings' object you want to import in other files
settings = Settings()