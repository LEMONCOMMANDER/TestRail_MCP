Feature: User Authentication

  Scenario: User logs in with valid credentials
    Given the user is on the login page
    When they enter a valid email and password and click Sign In
    Then they should be redirected to the dashboard

  Scenario: User cannot log in with an incorrect password
    Given the user is on the login page
    When they enter a valid email and an incorrect password
    Then they should see an authentication error message

  Scenario: User is locked out after five failed login attempts
    Given the user has failed to log in four times
    When they enter incorrect credentials a fifth time
    Then their account should be temporarily locked
    And they should be shown a lockout message with a retry time

  Scenario: User can reset their password via email
    Given the user is on the login page
    When they click the Forgot Password link and submit their email
    Then they should receive a password reset email within two minutes
