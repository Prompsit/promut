import re

re_flags = re.IGNORECASE | re.UNICODE

# manual regex matching with groups for training:
# 0: date of current update
# 1: timestamp of current update
# 2: "Ep." match for epochs
# 3: epoch number
# 4: update number
# 5: sentences read in current epoch
# 6: loss function result for current update
# 7: time between updates
# 8: words per second read between updates
# 9: gNorm value
# 10: learning rate value for current update
finetuning_regex = r'^\[(\d{4}-\d{2}-\d{2})\s(\d{2}:\d{2}:\d{2})\]\s(Ep)\.\s(\d+)\s:\sUp\.\s(\d+)\s:\sSen\.\s(\d+,\d+)\s:\sCost\s(\d+\.\d+)\s:\s' \
                    'Time\s(\d+\.\d+)\w\s:\s(\d+\.\d+)\swords/s\s:\sgNorm\s(\d+\.\d+)\s:\sL\.r\.\s(\d+\.\d+\w?-?\d+)$'

# manual regex matching with groups for validation hardcoded for bleu:
# 0: date of current update
# 1: timestamp of current validation step
# 2: validation flag "[valid]"
# 3: epoch number
# 4: update number
# 5: bleu score
validation_regex = r'\[(\d{4}-\d{2}-\d{2})\s(\d{2}:\d{2}:\d{2})\]\s\[(valid)\]\sEp\.\s(\d+)\s:\sUp\.\s(\d+)\s:\s(\w+(?:-\w+)*)\s:\s(\d+\.?\d*).*$'
