from BrainDevice.HomeAssistantService.HomeAssistant import update_label_value
import schedule
import time


def main():
    print("Home assistant service starting...")
    update_label_value("teste")
    schedule.every().sunday.at("9:00").do(job_with_argument, name="Peter")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()


def job_with_argument(name):
    print(f"I am {name}")
