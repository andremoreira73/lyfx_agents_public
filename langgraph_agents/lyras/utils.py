## Django settings
#from django.conf import settings
##

##################################################################
# this is a format that HAS TO BE like this
# After customizing a prompt, we pass the returned "create_prompt" function to the LG pre-defined agent
def customize_function_create_prompt(custom_system_prompt):
    def create_prompt(state):
        return [
            {
                "role": "system", 
                "content": custom_system_prompt
            }
        ] + state['messages']
    return create_prompt


