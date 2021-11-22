import sys
import re

class CommandList():
    def getCommandList(self):
        """
        Gets a list of active commands.

        The list should include all the target commands with interleaved words and labels.
        - Each command can be separated by pipe "|" or newline character "\n". It is recommended to
          put each command in parentheses to correctly parse the grammar.
        - Words/labels inside a command can be separated by a dot(".") or unlimited times of space(" "), tabulator("\t"), carriage return("\r").
        - Each word can start with alphabet and be followed by unlimited times of alphabet, dash, and
          apostrophe. (For example, john's).
        - Word can also be a number represented in numerical digit format. Sign and decimal points are also supported
          (For example, -15.46). This number will be interpolated as label `$integer` or `$real` based on the value of this number.
          Please check `GrammarSyntax.md` for more details on accepted grammar rules by SPEAR ASR Engine.
        """
        raise NotImplementedError("Please Implement this 'getCommandList' method")

    def mapCommands(self):
        """
        Gets a map of commands to a resulting command.
        Key: An input command via voice
        Value: A command that SpearSdk should return as a result
        As an example, if your application would like to receive "HELLO" command for the input commands "HELLO", "HELL LOW", and "ELMO"
        then the application should create a map where the value "HELLO" should be defined for keys "HELL LOW" and "ELMO".
        """
        raise NotImplementedError("Please Implement this 'mapCommands' method")

    def getGrammarLabels(self):
        """
        Gets a map of labels and assigned commands to it.
        Key: A label name must start with an alphabet and can be followed by unlimited times of alphabet, numeric digit, dash, underscore, and apostrophe.
        Value: A list of commands. Please check {@link #getCommandList()} for the format of the commands.
        There are three pre-defined labels available:
        - `$digit`: single numeric digit
        - `$integer`: any integer number(sign is optional)
        - `$real`: any real number(sign is optional)
        Please check `GrammarSyntax.md` for accepted grammar rules by SPEAR ASR Engine.
        """
        raise NotImplementedError("Please Implement this 'getGrammarLabels' method")

    def buildRegex(self):
        commandList = self.getCommandList()
        return self.getRegexFromCommandList(commandList)

    def getRegexFromCommandList(self, commandList):
        labelMap = self.getGrammarLabels()
        regex = self.buildLabels(labelMap) + self.buildBodySection(commandList, labelMap)
        return regex

    def buildLabels(self, labelMap):
        labelSection = []
        if labelMap != None:
            for key, value in labelMap.items():
                if (key != "" and value != ""):
                    labelSection.append("[${}: {}]\n".format(key, self.buildBodySection(value, labelMap)))
                else:
                    print("Error: Label '{}' or associated commands '{}' are not defined correctly.".format(key, value))
                    sys.exit(1)
        return ''.join(labelSection)

    def buildBodySection(self, commands, labelMap):
        bodySection = []
        for command in commands:
            if (command != ""):
                if ('|' in command): # has multiple commands
                    commandsFromCommand = command.split('|')
                    for com in commandsFromCommand:
                        bodySection.append(self.getFormattedCommand(com, labelMap))
                else:
                    bodySection.append(self.getFormattedCommand(command, labelMap))
        return '|'.join(bodySection)

    def getFormattedCommand(self, command, labelMap):
        if (self.isLabelDefined(command, labelMap)):
            if (command.startswith("(") and command.endswith(")")):
                resultCommand = command
            else:
                resultCommand = "({})".format(command.strip())
        else:
            print("{} is not defined in labelMap".format(command))
        return resultCommand

    def isLabelDefined(self, command, labelMap):
        labels = re.findall(r'\$[a-zA-Z][a-zA-z0-9\'-_]*', command)
        for label in labels:
            if (label not in ['$integer', '$real', 'digit']):
                if label[1:] not in labelMap:
                    print("Error: Label {} is not defined in the grammar.".format(label))
                    sys.exit(1) 
        return True


class DemoCommandList(CommandList):
    def getCommandList(self):
        demo_commands = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL", "INDIA",
            "JULIET", "KILO", "LIMA", "MIKE", "NOVEMBER", "OSCAR", "PAPA", "QUEBEC", "ROMEO", "SIERRA",
            "TANGO", "UNIFORM", "VICTOR", "WHISKEY", "XRAY", "YANKEE", "ZULU", "KWA BEK", "KEI BEK", "SWITCH GRAMMAR",
            "STOP SPEAR", "SWITCH LABEL GRAMMAR"]
        return demo_commands

    def mapCommands(self):
        commandMap = {}
        commandMap['KWA BEK'] = 'QUEBEC'
        commandMap['KEI BEK'] = 'QUEBEC'
        return commandMap

    def getGrammarLabels(self):
        return None

class LabelCommandList(CommandList):
    def getCommandList(self):
        label_commands = ["I.have.a.$pet",
            "($action1 light)|$action2",
            "My $pet weight 24.5 lb",
            "Her $vehicle values $integer dollars",
            "CLE stands for cleveland",
            "STOP SPEAR"]
        return label_commands

    def mapCommands(self):
        return None

    def getGrammarLabels(self):
        labelMap = {}
        labelMap['pet'] = ['dog', 'cat', 'rabbit', 'bird']
        labelMap['vehicle'] = ['bicycle', 'ship', 'car', 'plane']
        labelMap['action1'] = ['turn on', 'turn off']
        labelMap['action2'] = ['volumn up', 'volumn off']
        return labelMap


def main():
    demoCommandList = DemoCommandList()
    demo_command_list = demoCommandList.getCommandList()
    regex_demo_command_list = demoCommandList.getRegexFromCommandList(demo_command_list)
    print("regex for demo_command_list:\n{}".format(regex_demo_command_list))

    labelCommandList = LabelCommandList()
    label_command_list = labelCommandList.getCommandList()
    regex_label_command_list = labelCommandList.getRegexFromCommandList(label_command_list)
    print("regex for label_command_list:\n{}".format(regex_label_command_list))


if __name__ == '__main__':
    main()
