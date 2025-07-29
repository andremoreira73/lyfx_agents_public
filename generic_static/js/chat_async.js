// static_generic/js/chat_async.js
(function () {
  // This function will be called when the document is ready
  function initializeChatAsync() {
    var currentRequestId = null;
    var chatForm = $("#chat-form");
    var chatInput = document.getElementById("chat-input");
    var loadingIndicator = $("#loading-indicator");
    var cancelRequestBtn = $("#cancel-request");

    // Function to scroll chat to bottom
    function scrollToBottom() {
      var chatWindow = $("#chat-window");
      chatWindow.scrollTop($("#chat-messages").prop("scrollHeight"));
    }

    // Handle form submission
    chatForm.on("submit", function (event) {
      event.preventDefault();

      var message = $("#chat-input").val().trim();
      if (message === "") {
        return; // Don't send empty messages
      }
      $("#chat-input").val("");

      // Reset input height if auto-resize is enabled
      if (window.resetChatInputHeight) {
        window.resetChatInputHeight();
      } else if (chatInput) {
        chatInput.style.height = "auto";
        if ("overflowY" in chatInput.style) {
          chatInput.style.overflowY = "hidden";
        }
      }

      // Append user's message to UI
      $("#chat-messages").append(
        '<div class="d-flex justify-content-end mb-2">' +
          '<div class="message user-message">' +
          message +
          "</div>" +
          "</div>"
      );
      scrollToBottom();

      // Show loading indicator and cancel button
      loadingIndicator.show();
      cancelRequestBtn.show();

      // Extract URL parameters
      var urlParams = new URLSearchParams(window.location.search);
      var agentName = urlParams.get("agent_name");
      var assistantId = urlParams.get("assistant");
      var vectorStoreId = urlParams.get("vector_store");

      // Get the base URL for async endpoints
      var chatUrl = window.location.pathname;
      var asyncUrl = chatUrl.includes("/chat_plus/")
        ? "/chat_plus/chat_async/"
        : "/chat/chat_async/";

      // Send message to async endpoint
      $.ajax({
        url: asyncUrl,
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({
          message: message,
          agent_name: agentName,
          assistant_id: assistantId,
          vector_store: vectorStoreId,
        }),
        success: function (data) {
          if (data.request_id) {
            currentRequestId = data.request_id;
            pollForResult(data.request_id);
          } else if (data.reply) {
            // Handle direct reply (fallback)
            displayReply(data.reply);
          } else if (data.error) {
            displayError(data.error);
          }
        },
        error: function (xhr, status, error) {
          loadingIndicator.hide();
          cancelRequestBtn.hide();
          console.error("AJAX Error:", status, error);
          displayError("Failed to send message. Please try again.");
        },
      });
    });

    // Handle cancel button
    cancelRequestBtn.on("click", function () {
      if (currentRequestId) {
        var cancelUrl = window.location.pathname.includes("/chat_plus/")
          ? "/chat_plus/cancel_request/"
          : "/chat/cancel_request/";

        $.ajax({
          url: cancelUrl,
          type: "POST",
          data: JSON.stringify({
            request_id: currentRequestId,
          }),
          contentType: "application/json",
          success: function () {
            loadingIndicator.hide();
            cancelRequestBtn.hide();
            displaySystemMessage("Request cancelled");
            currentRequestId = null;
          },
        });
      }
    });

    function pollForResult(requestId) {
      var startTime = Date.now();
      var maxPollTime = 120000; // 2 minutes in milliseconds

      var checkUrl = window.location.pathname.includes("/chat_plus/")
        ? "/chat_plus/check_status/"
        : "/chat/check_status/";

      var checkStatus = function () {
        // Check if we've exceeded the maximum polling time
        if (Date.now() - startTime > maxPollTime) {
          loadingIndicator.hide();
          cancelRequestBtn.hide();
          displayError(
            "Request timed out after waiting too long. Please try again."
          );
          currentRequestId = null;
          return;
        }

        $.ajax({
          url: checkUrl,
          type: "GET",
          data: {
            request_id: requestId,
          },
          success: function (data) {
            if (data.status === "completed") {
              loadingIndicator.hide();
              cancelRequestBtn.hide();
              displayReply(data.reply);
              currentRequestId = null;
            } else if (data.status === "error") {
              loadingIndicator.hide();
              cancelRequestBtn.hide();
              displayError(data.reply);
              currentRequestId = null;
            } else {
              // Continue polling
              setTimeout(checkStatus, 1000);
            }
          },
          error: function (xhr, status, error) {
            loadingIndicator.hide();
            cancelRequestBtn.hide();
            console.error("Polling Error:", status, error);
            displayError("Failed to get response. Please try again.");
            currentRequestId = null;
          },
          // Add a timeout to the AJAX request itself
          timeout: 5000, // 5 seconds timeout for each individual AJAX request
        });
      };

      // Start polling
      checkStatus();
    }

    function displayReply(reply) {
      // Format and display the reply
      var formattedReply = reply.replace(/\n/g, "<br>");

      $("#chat-messages").append(
        '<div class="d-flex justify-content-start mb-2">' +
          '<div class="message assistant-message">' +
          formattedReply +
          "</div>" +
          "</div>"
      );

      scrollToBottom();
    }

    function displayError(error) {
      $("#chat-messages").append(
        '<div class="d-flex justify-content-start mb-2">' +
          '<div class="message assistant-message text-danger">' +
          "Error: " +
          error +
          "</div>" +
          "</div>"
      );

      scrollToBottom();
    }

    function displaySystemMessage(message) {
      $("#chat-messages").append(
        '<div class="d-flex justify-content-center mb-2">' +
          '<div class="message system-message">' +
          message +
          "</div>" +
          "</div>"
      );
      scrollToBottom();
    }
  }

  // Initialize when document is ready
  $(document).ready(initializeChatAsync);
})();
