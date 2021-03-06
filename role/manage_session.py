from role.manage_notification import show_notification
from role import dt, logging, Service, webdriver, time, os, BeautifulSoup, pd, config_dict, projdir_name


def session_manager():
    logging.info("session_manager had started")

    c = 0
    while True:
        c += 1
        print(f'\nCurrent Time : {dt.datetime.strftime(dt.datetime.now(), "%Y-%m-%d %I:%M:%S%p")}\n')
        try:
            scrap_session()
            break
        except Exception as err:
            logging.error(f"Error at Session Manager : {err}", stack_info=True)
            show_notification(title="Error at Session Manager", message_text=err)
            if c >= 5:
                break
            time.sleep(60)
            continue

    logging.info("session_manager had stopped")


def scrap_session():
    print("Starting Session ......\n")
    logging.info("Starting Session")

    chromedriver_path = "/".join([projdir_name, 'chromedriver'])
    service = Service(chromedriver_path)
    service.start()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options = options.to_capabilities()
    driver = webdriver.Remote(service.service_url, options)

    do_login(driver=driver)

    attendance_card_list = get_attendance_events(driver=driver)

    attendance_link_list = get_activity_links(event_card_list=attendance_card_list)

    for attendance_link in attendance_link_list:
        driver.get(attendance_link)
        driver.implicitly_wait(10)
        status_link_list = get_sub_activity_list(driver=driver)
        make_me_present(driver=driver, status_link_list=status_link_list)
        driver.implicitly_wait(10)
        # driver.close()

    driver.quit()

    print("\nEnding Session ......\n")
    logging.info("Ending Session ......")


def do_login(driver=None):
    if config_dict["login_credentials"]["username"] == "username":
        username = os.environ.get('ROLE_USERNAME')
    else:
        username = config_dict["login_credentials"]["username"]
    if config_dict["login_credentials"]["password"] == "password":
        password = os.environ.get('ROLE_PASSWORD')
    else:
        password = config_dict["login_credentials"]["password"]

    print("Logging In ......")
    logging.info("Logging In")
    # driver.get("https://cse.rgpvonline.org/calendar/view.php?view=upcoming")
    driver.get("https://cse.rgpvonline.org/calendar/view.php?view=day")
    driver.implicitly_wait(10)
    username_input = driver.find_element_by_xpath('//*[@id="username"]')
    password_input = driver.find_element_by_xpath('//*[@id="password"]')
    username_input.send_keys(username)
    password_input.send_keys(password)
    login_btn = driver.find_element_by_xpath('//*[@id="loginbtn"]')
    driver.find_element_by_xpath('//*[@id="rememberusername"]').click()
    login_btn.click()
    print("Successfully Logged In !!!")
    logging.info("Successfully Logged In")


def get_attendance_events(driver=None):
    logging.info("Getting Attendance Event Card List for Today.")
    event_soup = BeautifulSoup(driver.page_source, "lxml")

    div_list = event_soup.find_all("div")

    event_card_list = []
    for div in div_list:
        if div.has_attr("class"):
            if div["class"] == ["card", "rounded"]:
                parent_div = div.find_parent("div")
                if parent_div.has_attr("data-event-eventtype"):
                    if parent_div["data-event-eventtype"] == "attendance":
                        event_card_list.append(div)

    return event_card_list


def get_activity_links(event_card_list=None):
    logging.info("Getting Attendance Activity Links From Event Card List for Today.")
    activity_link_list = []
    for event_card in event_card_list:
        card_activity_link = event_card.find("a", {"class": "card-link"})["href"]
        activity_link_list.append(card_activity_link)

    return activity_link_list


def get_sub_activity_list(driver=None):
    sub_name = driver.find_element_by_css_selector("h1").text
    logging.info(f"Checking Active Attendance Links for {sub_name}")
    sub_soup = BeautifulSoup(driver.page_source, "lxml")

    attendance_table = sub_soup.find("table", {"class": "generaltable"})

    attendance_df = pd.read_html(str(attendance_table))[0]

    status_ser = attendance_df["Status"][(attendance_df["Status"] != "Present") & (attendance_df["Status"] != "?")]

    status_link_list = []
    if not status_ser.empty:
        # status_link_list = sub_soup.find_all("a")
        status_link_list = driver.find_elements_by_link_text("Submit attendance")
        status_link_list = [i.get_attribute("href") for i in status_link_list]

    print()
    return status_link_list


def make_me_present(driver=None, status_link_list=None):
    sub_name = driver.find_element_by_css_selector("h1").text
    logging.info(f"Got {len(status_link_list)} Active Attendance Link for {sub_name}")
    print(sub_name)
    print(status_link_list)
    if len(status_link_list):
        logging.info("Trying to make you present ......")
        for status_link in status_link_list:
            driver.get(status_link)
            driver.implicitly_wait(10)

            try:

                radio_elems_labels = driver.find_elements_by_css_selector("label.form-check-inline")

                for radio_elem_label in radio_elems_labels:
                    span_text = radio_elem_label.find_element_by_css_selector("span.statusdesc").text
                    if span_text == "Present":
                        radio_input = radio_elem_label.find_element_by_css_selector("input.form-check-input")
                        radio_input.click()
                        driver.find_element_by_xpath('//*[@id="id_submitbutton"]').click()
                        driver.implicitly_wait(10)
                        show_notification(title="You Are Present Now !!!", message_text=sub_name)

            except Exception as exp:
                logging.error(f"Error : {exp} at make_me_present", stack_info=True)
                show_notification(title="Error Occurred!!!", message_text=exp)


if __name__ == '__main__':
    session_manager()
