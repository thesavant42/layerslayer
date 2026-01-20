# fslog errors and solutions

## Problem Statement:

If a container has not yet been peek-indexed but a user tries to view the fslog for that image,
    - the API currently throws a 500 http error on the api console,
    -  but throws an unhandled exception
    -  and does not alert the user that there has not yet been an indexing. 

---

Screenshot 1 of 3

![Exception Screenshot 1 of 3](/plans/fslog-enhancements/exception-001.png)

---

Screenshot 2 of 3
![Exception Screenshot 2 of 3](/plans/fslog-enhancements/exception-002.png)

---

Screenshot 3 of 3
![Exception Screenshot 3 of 3](/plans/fslog-enhancements/exception-003.png)
Screenshot 3 of 3

The full text of the log is available in the [raw log here.](plans\fslog-enhancements\exception.log)
--

## Proposed solution:

- Instead, the perferred flow for `/fslog?` should be:
    - If a user tries to `fslog` a layer that does not yet exist:
        - The layer(s) should then be `peeked` and stored in the database per usual, and the layer(s) should then be displayed per the normal flow.
        - **Open Question**: Is there a programmatic function to peek a single layer in this versio of the code?
        - A:
            - A loading message can be displayed to the user
        - This enables aa route that **does not require the entire container be pre-indexed first**.
        - This increased granular control over the output increases efficiency, which is on-brand for this project.

---

- [ ] Task 1. Improve error handling
    - stack traces are helpful but there should be a programatic way to notify the user of an error.
    - A 5xx status code should not cause an application exception, or a 404, those messages can be forwarded 
- [ ] Task 2. Implement new `/fslog?` flow described in the Proposed Solution.
