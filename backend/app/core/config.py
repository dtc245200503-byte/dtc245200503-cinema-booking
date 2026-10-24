from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://cinema_app:change-me@localhost:3306/cinema?charset=utf8mb4"
    secret_key: str = "change-me"
    access_token_minutes: int = 480
    hold_minutes: int = 10          # thời gian giữ ghế chờ thanh toán
    max_seats_per_booking: int = 8
    vip_multiplier_percent: int = 150
    upload_dir: str = "/data/uploads"        # nơi lưu ảnh poster (volume dùng chung với Nginx)
    max_poster_bytes: int = 2 * 1024 * 1024
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
